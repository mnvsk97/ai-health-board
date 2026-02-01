from __future__ import annotations

import asyncio
import time
import uuid

import httpx
from fastapi import FastAPI, HTTPException

from .compliance import simulate_guideline_change
from . import daily_rooms
from .models import Run
from .grader_agent import grade_transcript_comprehensive_async
from . import redis_store
from . import run_orchestrator

app = FastAPI(title="AI Health Board")


@app.post("/runs")
async def create_run(payload: dict) -> dict:
    run_id = f"run_{uuid.uuid4().hex[:10]}"
    mode = payload.get("mode", "voice_voice")
    target_type = payload.get("target_type", "pipecat")
    target_url = payload.get("target_url")
    if target_type == "url" or target_url:
        mode = "text_text"
        if not target_url:
            raise HTTPException(status_code=400, detail="target_url required for url target_type")
        if not payload.get("input_selector") or not payload.get("response_selector"):
            raise HTTPException(status_code=400, detail="input_selector and response_selector required for url target_type")
    room_url = None
    room_name = None
    room_token = None
    if mode != "text_text" and target_type != "url" and not target_url:
        room = daily_rooms.create_room(expiry_seconds=900)
        room_name = room.get("name")
        room_url = room.get("url")
        room_token = daily_rooms.get_meeting_token(room_name, owner=True, expiry_seconds=900)

    run = Run(
        run_id=run_id,
        status="pending",
        scenario_ids=payload.get("scenario_ids", []),
        mode=mode,
        room_url=room_url,
        room_name=room_name,
        room_token=room_token,
        started_at=time.time(),
        updated_at=time.time(),
    )
    redis_store.create_run(run)

    agent_type = payload.get("agent_type", "intake")

    if run.mode == "text_text" and (target_type == "url" or target_url):
        async def _browserbase_run():
            run.status = "running"
            redis_store.update_run(run)
            scenarios = redis_store.list_scenarios()
            scenario = next((s for s in scenarios if s.scenario_id in run.scenario_ids), None)
            if scenario:
                from .tester_browserbase import BrowserbaseChatConfig, run_browserbase_test
                config = BrowserbaseChatConfig(
                    url=target_url or "",
                    input_selector=str(payload.get("input_selector")),
                    response_selector=str(payload.get("response_selector")),
                    send_selector=payload.get("send_selector"),
                    transcript_selector=payload.get("transcript_selector"),
                    max_turns=int(payload.get("max_turns") or 4),
                    timeout_ms=int(payload.get("timeout_ms") or 45000),
                    settle_ms=int(payload.get("settle_ms") or 1500),
                )
                await asyncio.to_thread(run_browserbase_test, config, scenario, run_id)
            run.status = "completed"
            redis_store.update_run(run)
        asyncio.create_task(_browserbase_run())
    elif run.mode == "text_text":
        async def _run():
            run.status = "running"
            redis_store.update_run(run)
            run_orchestrator.run_text(run_id, run.scenario_ids, agent_type)
            run.status = "completed"
            redis_store.update_run(run)
        asyncio.create_task(_run())
    else:
        # Trigger target agent to join room
        try:
            settings = run_orchestrator.load_settings()
            with httpx.Client(timeout=10) as client:
                client.post(
                    f"{settings.get('target_agent_url')}/bot",
                    json={"room_url": room_url, "token": room_token, "body": {"agent_type": agent_type}},
                )
        except Exception:
            pass

        async def _voice_run():
            run.status = "running"
            redis_store.update_run(run)
            scenarios = redis_store.list_scenarios()
            scenario = next((s for s in scenarios if s.scenario_id in run.scenario_ids), None)
            if scenario:
                from .tester_voice import run_voice_test, voice_test_config
                config = voice_test_config(room_url=room_url, token=room_token, scenario=scenario)
                await run_voice_test(config, run_id=run_id)
            run.status = "completed"
            redis_store.update_run(run)
        asyncio.create_task(_voice_run())

    return {"run_id": run_id, "status": run.status, "room_url": room_url}


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    run = redis_store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run.model_dump()


@app.get("/runs/{run_id}/transcript")
def get_transcript(run_id: str) -> dict:
    transcript = redis_store.get_transcript(run_id)
    return {"run_id": run_id, "transcript": [t.model_dump() for t in transcript]}


@app.get("/runs/{run_id}/report")
def get_report(run_id: str) -> dict:
    grading = redis_store.get_grading(run_id)
    if not grading:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"run_id": run_id, "grading": grading}


@app.post("/runs/{run_id}/grade")
async def grade_run(run_id: str, payload: dict | None = None) -> dict:
    run = redis_store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    transcript = redis_store.get_transcript(run_id)
    if not transcript:
        raise HTTPException(status_code=400, detail="Transcript not available")

    payload = payload or {}
    scenario_id = payload.get("scenario_id") or (run.scenario_ids[0] if run.scenario_ids else None)
    if not scenario_id:
        raise HTTPException(status_code=400, detail="scenario_id required")
    scenario = redis_store.get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    run.status = "grading"
    redis_store.update_run(run)

    comprehensive = await grade_transcript_comprehensive_async(scenario, transcript)
    grading = {
        "scenario_id": scenario_id,
        "mode": "comprehensive",
        "comprehensive": comprehensive.model_dump(),
    }

    redis_store.save_grading(run_id, grading)
    run.status = "completed"
    redis_store.update_run(run)
    return {"run_id": run_id, "grading": grading}


@app.get("/runs")
def list_runs(status: str | None = None, limit: int = 50) -> dict:
    """List all runs with optional status filtering."""
    runs = redis_store.list_runs(status=status, limit=limit)
    return {"runs": [r.model_dump() for r in runs]}


@app.post("/runs/{run_id}/stop")
def stop_run(run_id: str) -> dict:
    """Stop/cancel a running test."""
    run = redis_store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    run.status = "canceled"
    redis_store.update_run(run)
    return {"status": "canceled"}


@app.get("/scenarios")
def list_scenarios() -> dict:
    scenarios = redis_store.list_scenarios()
    return {"scenarios": [s.model_dump() for s in scenarios]}


@app.post("/compliance/simulate-change")
def simulate_change(payload: dict) -> dict:
    guideline_id = payload.get("guideline_id")
    target_id = payload.get("target_id", "default")
    if not guideline_id:
        raise HTTPException(status_code=400, detail="guideline_id required")
    scenario = simulate_guideline_change(guideline_id, target_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="guideline not found")
    return {"status": "outdated", "new_scenario": scenario.model_dump()}
