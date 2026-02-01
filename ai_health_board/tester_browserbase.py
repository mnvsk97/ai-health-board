from __future__ import annotations

import asyncio
import json
import subprocess
import time
from dataclasses import dataclass

from loguru import logger

from .models import Scenario, TranscriptEntry
from . import redis_store
from .tester_agent import (
    plan_attack,
    next_message,
    init_turn_state,
    advance_turn,
    generate_attack_with_score,
)
from .observability import trace_op


@dataclass
class BrowserbaseChatConfig:
    url: str
    input_selector: str
    response_selector: str
    transcript_selector: str | None = None
    send_selector: str | None = None
    max_turns: int = 4
    timeout_ms: int = 45000
    settle_ms: int = 1500


def _run_stagehand_turn(config: BrowserbaseChatConfig, message: str) -> dict[str, object]:
    cmd = [
        "node",
        "scripts/stagehand_chat_turn.mjs",
        "--url",
        config.url,
        "--message",
        message,
        "--input-selector",
        config.input_selector,
        "--response-selector",
        config.response_selector,
        "--timeout-ms",
        str(config.timeout_ms),
        "--settle-ms",
        str(config.settle_ms),
    ]
    if config.send_selector:
        cmd += ["--send-selector", config.send_selector]
    if config.transcript_selector:
        cmd += ["--transcript-selector", config.transcript_selector]

    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    lines = result.stdout.strip().splitlines()
    if not lines:
        raise RuntimeError("Stagehand returned no output")
    payload = None
    for line in reversed(lines):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
            break
        except json.JSONDecodeError:
            continue
    if payload is None:
        raise RuntimeError(f"Stagehand returned no JSON payload. Last line: {lines[-1]}")
    return payload


def _strip_tester_wrapper(message: str) -> str:
    import re

    lowered = message.lower()
    quoted = re.findall(r"\"([^\"]+)\"", message, flags=re.DOTALL)
    if quoted:
        longest = max(quoted, key=len)
        return longest.strip()
    for marker in (
        "tester message",
        "here's my next message",
        "here is my next message",
        "my next tester message",
        "my goal here is",
        "this message",
        "this prompt",
    ):
        if marker in lowered:
            return message.split(marker, 1)[0].strip()
    return message.strip()


@trace_op("tester.run_browserbase_test")
def run_browserbase_test(
    config: BrowserbaseChatConfig,
    scenario: Scenario,
    run_id: str,
    enable_scoring: bool = True,
) -> dict[str, object]:
    """Run a browserbase test with optional attack scoring.

    Args:
        config: Browser chat configuration
        scenario: Test scenario
        run_id: Unique run identifier
        enable_scoring: If True, scores each attack with Weave (default: True)

    Returns:
        Dict with test results including scores if enabled
    """
    plan = plan_attack(scenario)
    turn_state = init_turn_state()
    last_response = ""
    last_seen = 0
    last_by_role: dict[str, str] = {}
    attack_scores = []

    for turn_index in range(int(config.max_turns)):
        # Generate attack with scoring to match Pipecat tester behavior
        if enable_scoring:
            try:
                attack_result = asyncio.run(
                    generate_attack_with_score(
                        scenario=scenario,
                        target_response=last_response,
                        plan=plan,
                        turn_index=turn_index,
                        run_id=run_id,
                    )
                )
                tester_message = _strip_tester_wrapper(attack_result["attack"])
                attack_scores.append({
                    "turn": turn_index,
                    "score": attack_result["score"],
                    "effectiveness": attack_result["effectiveness"],
                    "call_id": attack_result["call_id"],
                })
                logger.info(
                    f"Turn {turn_index}: effectiveness={attack_result['effectiveness']:.2f}"
                )
            except Exception as e:
                logger.warning(f"Scoring failed, falling back to unscored: {e}")
                tester_message = _strip_tester_wrapper(
                    next_message(scenario, last_response, plan, turn_index)
                )
        else:
            tester_message = _strip_tester_wrapper(
                next_message(scenario, last_response, plan, turn_index)
            )

        if tester_message:
            if last_by_role.get("tester") != tester_message:
                redis_store.append_transcript(
                    run_id,
                    TranscriptEntry(role="tester", content=tester_message, timestamp=time.time()),
                )
                last_by_role["tester"] = tester_message

        result = _run_stagehand_turn(config, tester_message)
        messages = result.get("messages") or []
        if isinstance(messages, list):
            new_messages = messages[last_seen:]
            for msg in new_messages:
                if not isinstance(msg, dict):
                    continue
                role = (msg.get("role") or "").lower()
                if role not in {"assistant", "ai", "bot"}:
                    continue
                content = msg.get("content") or ""
                if not content:
                    continue
                mapped_role = "target"
                if last_by_role.get(mapped_role) == str(content):
                    continue
                redis_store.append_transcript(
                    run_id,
                    TranscriptEntry(role=mapped_role, content=str(content), timestamp=time.time()),
                )
                last_by_role[mapped_role] = str(content)
            last_seen = len(messages)

        response_text = str(result.get("response_text") or "")
        if response_text and not messages:
            if last_by_role.get("target") == response_text:
                response_text = ""
            else:
                last_by_role["target"] = response_text
            redis_store.append_transcript(
                run_id,
                TranscriptEntry(role="target", content=response_text, timestamp=time.time()),
            )
        last_response = response_text
        advance_turn(turn_state, prompt_used=tester_message)

    # Calculate average effectiveness
    avg_effectiveness = 0.0
    if attack_scores:
        avg_effectiveness = sum(s["effectiveness"] for s in attack_scores) / len(attack_scores)

    return {
        "run_id": run_id,
        "turns_completed": len(attack_scores) if attack_scores else int(config.max_turns),
        "attack_scores": attack_scores,
        "avg_effectiveness": avg_effectiveness,
        "prompts_used": turn_state.get("prompts_used", []),
    }
