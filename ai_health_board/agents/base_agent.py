from __future__ import annotations

import os
import asyncio
import json
import time
from typing import Any

from loguru import logger
from openai import OpenAI

from ..models import TranscriptEntry
from ..observability import init_weave, trace_op, trace_attrs
from .. import redis_store
from .tools import TOOL_REGISTRY, tool_schemas


def build_agent(agent_name: str, system_prompt: str) -> dict[str, str]:
    init_weave()
    return {"agent_name": agent_name, "system_prompt": system_prompt}


def _get_model_name(base_url: str) -> str:
    if "openai.com" in base_url.lower():
        return "gpt-4o-mini"
    return os.getenv("OPENAI_MODEL", "openai-main/gpt-4o-mini")


def _get_openai_client() -> tuple[OpenAI, str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    return OpenAI(api_key=api_key, base_url=base_url, timeout=20), base_url


async def create_pipeline(agent: dict[str, str], transport: Any) -> tuple[Any, Any]:
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.processors.aggregators.llm_context import LLMContext
    from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
    from pipecat.services.openai.llm import OpenAILLMService
    from pipecat.services.openai.stt import OpenAISTTService
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat.services.cartesia.tts import CartesiaTTSService
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = _get_model_name(base_url)

    llm = OpenAILLMService(api_key=api_key, base_url=base_url, model=model)
    stt = OpenAISTTService(api_key=api_key, base_url=base_url)

    cartesia_key = os.getenv("CARTESIA_API_KEY")
    if not cartesia_key:
        raise ValueError("CARTESIA_API_KEY is required")

    tts = CartesiaTTSService(
        api_key=cartesia_key,
        model="sonic-english",
        voice_id=os.getenv("CARTESIA_VOICE_ID", ""),
    )

    context = LLMContext([{ "role": "system", "content": agent["system_prompt"] }])
    context_aggregator = LLMContextAggregatorPair(context)

    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),
        llm,
        tts,
        transport.output(),
        context_aggregator.assistant(),
    ])

    return pipeline, context_aggregator


async def run_agent(
    agent: dict[str, str],
    room_url: str,
    token: str | None = None,
    run_id: str | None = None,
) -> None:
    from pipecat.frames.frames import EndFrame, LLMMessagesUpdateFrame
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineParams, PipelineTask
    from pipecat.transports.daily.transport import DailyParams, DailyTransport
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    transport = DailyTransport(
        room_url,
        token,
        agent["agent_name"],
        DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            transcription_enabled=True,
            audio_in_user_tracks=False,
            vad_enabled=True,
            vad_audio_passthrough=True,
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    pipeline, context_aggregator = await create_pipeline(agent, transport)
    user_aggregator = context_aggregator.user()
    assistant_aggregator = context_aggregator.assistant()
    task = PipelineTask(
        pipeline,
        params=PipelineParams(allow_interruptions=True, enable_metrics=True),
    )

    @transport.event_handler("on_participant_left")
    async def on_participant_left(_transport, _participant, _reason):
        await task.queue_frame(EndFrame())

    if run_id:
        @user_aggregator.event_handler("on_user_turn_stopped")
        async def on_user_turn_stopped(_aggregator, _strategy, message):
            content = message.content or getattr(message, "text", "")
            if content:
                logger.info("intake received user turn: {}", content[:160])
                redis_store.append_transcript(
                    run_id,
                    TranscriptEntry(role="tester", content=content, timestamp=time.time()),
                )

        @assistant_aggregator.event_handler("on_assistant_turn_stopped")
        async def on_assistant_turn_stopped(_aggregator, message):
            content = message.content or getattr(message, "text", "")
            if content:
                logger.info("intake produced assistant turn: {}", content[:160])
                redis_store.append_transcript(
                    run_id,
                    TranscriptEntry(role="target", content=content, timestamp=time.time()),
                )

    runner = PipelineRunner()
    try:
        runner_task = asyncio.create_task(runner.run(task))
        await task.queue_frames([
            LLMMessagesUpdateFrame(
                [{"role": "user", "content": "Hello, I need healthcare help."}],
                run_llm=True,
            )
        ])
        await runner_task
    finally:
        logger.info("Session ended")


async def bot(agent: dict[str, str], args: Any) -> None:
    from pipecatcloud.agent import DailySessionArguments
    if not isinstance(args, DailySessionArguments):
        raise ValueError("DailySessionArguments required")
    run_id = None
    if isinstance(args.body, dict):
        run_id = args.body.get("run_id")
    await run_agent(agent, args.room_url, args.token, run_id=run_id)


@trace_op("pipecat.handle_message")
async def handle_message(agent: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    msg = payload.get("message")
    session_id = payload.get("session_id") or payload.get("sessionId")
    if not msg or not session_id:
        return {"error": "message and session_id required"}
    with trace_attrs({"session.id": session_id, "agent.name": agent["agent_name"]}):
        messages = payload.get("messages") or [
            {"role": "system", "content": agent["system_prompt"]}
        ]
        if messages:
            messages = [m for m in messages if m.get("role") != "tool"]
        messages.append({"role": "user", "content": msg})

        client, base_url = _get_openai_client()
        model = _get_model_name(base_url)

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tool_schemas(),
        )

        assistant_text = response.choices[0].message.content or ""
        tool_calls = response.choices[0].message.tool_calls or []

        for call in tool_calls:
            tool_fn = TOOL_REGISTRY.get(call.function.name)
            if not tool_fn:
                continue
            arguments = call.function.arguments
            try:
                tool_args = json.loads(arguments) if isinstance(arguments, str) else arguments
            except Exception:
                tool_args = {}
            tool_result = tool_fn(**tool_args)
            messages.append({"role": "tool", "name": call.function.name, "content": str(tool_result)})

        if tool_calls:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
            )
            assistant_text = response.choices[0].message.content or ""

        messages.append({"role": "assistant", "content": assistant_text})
        return {"text": assistant_text, "messages": messages}
