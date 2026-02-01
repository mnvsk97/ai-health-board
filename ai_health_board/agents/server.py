from __future__ import annotations

import asyncio
import json
import os
import time
from loguru import logger
from fastapi import FastAPI, HTTPException, Request
import uvicorn

from pipecatcloud.agent import DailySessionArguments

from .intake_agent import make_intake_agent
from .refill_agent import make_refill_agent
from .base_agent import bot as run_bot, handle_message as handle_agent_message
from .. import redis_store
from ..models import Run
from ..tester_voice import run_voice_test, voice_test_config

app = FastAPI()

intake_agent = make_intake_agent()
refill_agent = make_refill_agent()


async def handle_session_args(args: DailySessionArguments) -> dict:
    body = args.body or {}
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            body = {}
    if not isinstance(body, dict):
        body = {}
    agent_type = body.get("agent_type") or body.get("agentType") or "intake"
    logger.info(
        "handle_session_args agent_type={} room_url_present={} run_id={}",
        agent_type,
        bool(args.room_url),
        body.get("run_id"),
    )
    if agent_type == "tester":
        scenario_id = body.get("scenario_id")
        if not scenario_id:
            raise HTTPException(status_code=400, detail="scenario_id required for tester agent")
        scenario = redis_store.get_scenario(str(scenario_id))
        if not scenario:
            raise HTTPException(status_code=404, detail="scenario not found")
        max_turns = int(body.get("max_turns") or 4)
        run_id = str(body.get("run_id") or f"run_{int(time.time())}")
        run = Run(
            run_id=run_id,
            status="running",
            scenario_ids=[scenario.scenario_id],
            mode="voice_voice",
            room_url=str(args.room_url),
            room_token=str(args.token) if args.token else None,
            started_at=time.time(),
            updated_at=time.time(),
        )
        redis_store.create_run(run)
        config = voice_test_config(
            str(args.room_url),
            str(args.token) if args.token else None,
            scenario,
            max_turns=max_turns,
        )
        asyncio.create_task(run_voice_test(config, run_id))
        return {"status": "ok", "agent": "tester", "run_id": run_id}

    agent = intake_agent if agent_type == "intake" else refill_agent
    asyncio.create_task(run_bot(agent, args))
    return {"status": "ok", "agent": agent_type}


@app.post("/bot")
async def bot_endpoint(request: Request, payload: dict | None = None):
    if payload is None:
        payload = {}
    if not payload:
        raw_body = await request.body()
        logger.info("Received /bot raw body bytes={}, content-type={}", len(raw_body or b""), request.headers.get("content-type"))
        if raw_body:
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except json.JSONDecodeError:
                payload = {}
    logger.info("Received /bot payload keys: {}", list(payload.keys()))
    if not payload:
        env_room = os.getenv("DAILY_ROOM_URL")
        if env_room:
            args = DailySessionArguments(
                session_id=os.getenv("SESSION_ID") or f"session_{int(time.time())}",
                room_url=env_room,
                token=os.getenv("DAILY_TOKEN") or os.getenv("DAILY_ROOM_TOKEN"),
                body={},
            )
            result = await handle_session_args(args)
            result["source"] = "env"
            return result
        return {"status": "noop"}
    def find_value(obj, keys):
        if not isinstance(obj, dict):
            return None
        for k in keys:
            if k in obj:
                return obj.get(k)
        for v in obj.values():
            if isinstance(v, dict):
                found = find_value(v, keys)
                if found is not None:
                    return found
        return None

    room_url = find_value(payload, ["room_url", "roomUrl", "dailyRoom", "room"])
    token = find_value(payload, ["token", "dailyToken"])
    session_id = find_value(payload, ["session_id", "sessionId"])
    body = payload.get("body") or payload.get("data") or {}
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            body = {}
    if not isinstance(body, dict):
        body = {}
    agent_type = (
        body.get("agent_type")
        or body.get("agentType")
        or payload.get("agent_type")
        or payload.get("agentType")
        or ("tester" if body.get("scenario_id") else "intake")
    )
    def find_value(obj, keys):
        if not isinstance(obj, dict):
            return None
        for k in keys:
            if k in obj:
                return obj.get(k)
        for v in obj.values():
            if isinstance(v, dict):
                found = find_value(v, keys)
                if found is not None:
                    return found
        return None

    if not body.get("scenario_id"):
        body["scenario_id"] = find_value(payload, ["scenario_id", "scenarioId"])
    if not body.get("run_id"):
        body["run_id"] = find_value(payload, ["run_id", "runId"])
    if not body.get("room_url"):
        body["room_url"] = find_value(payload, ["room_url", "roomUrl", "dailyRoom", "room"])
    if not body.get("token"):
        body["token"] = find_value(payload, ["token", "dailyToken"])
    if not body.get("max_turns"):
        body["max_turns"] = find_value(payload, ["max_turns", "maxTurns"])
    if not session_id:
        session_id = body.get("session_id") or body.get("sessionId")
    if not room_url:
        room_url = body.get("room_url") or body.get("roomUrl")
    if not token:
        token = body.get("token") or body.get("dailyToken")
    def header_value(name: str) -> str | None:
        for key, value in request.headers.items():
            if key.lower() == name.lower():
                return value
        return None

    if not room_url:
        room_url = header_value("x-daily-room-url")
    if not token:
        token = header_value("x-daily-room-token")
    if not room_url:
        room_url = os.getenv("DAILY_ROOM_URL")
    if not token:
        token = os.getenv("DAILY_TOKEN") or os.getenv("DAILY_ROOM_TOKEN")
    if not session_id:
        session_id = os.getenv("SESSION_ID")
    if not session_id:
        session_id = header_value("x-daily-session-id")
    if not room_url:
        header_keys = [key for key in request.headers.keys()]
        daily_headers = {
            key: ("<redacted>" if request.headers.get(key) else None)
            for key in header_keys
            if "daily" in key.lower() or "room" in key.lower() or "token" in key.lower()
        }
        logger.info("Missing room_url; header keys={} daily_headers={}", header_keys, daily_headers)

    if not room_url:
        raise HTTPException(status_code=400, detail="room_url required")
    if not session_id:
        session_id = str(body.get("run_id") or room_url or f"session_{int(time.time())}")
    body["agent_type"] = agent_type
    args = DailySessionArguments(session_id=session_id, room_url=room_url, token=token, body=body)
    try:
        return await handle_session_args(args)
    except HTTPException as exc:
        logger.warning("handle_session_args failed: status={} detail={}", exc.status_code, exc.detail)
        raise
    except Exception:
        logger.exception("handle_session_args failed with unexpected error")
        raise


@app.post("/message")
async def message(payload: dict):
    agent_type = payload.get("agent_type", "intake")
    agent = intake_agent if agent_type == "intake" else refill_agent
    result = await handle_agent_message(agent, payload)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/status")
async def status():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {"status": "ok"}


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.getenv("PIPECAT_HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", os.getenv("PIPECAT_PORT", "7860"))),
        log_level="info",
    )
