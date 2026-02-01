from __future__ import annotations

import time

import httpx

from .config import load_settings
from .grader_agent import grade_transcript_comprehensive
from .models import Scenario, TranscriptEntry
from . import redis_store
from .tester_agent import plan_attack, next_message, init_turn_state, advance_turn


def _send_message(agent_type: str, session_id: str, message: str, messages: list[dict]) -> dict:
    settings = load_settings()
    payload = {
        "agent_type": agent_type,
        "session_id": session_id,
        "message": message,
        "messages": messages,
    }
    with httpx.Client(timeout=30) as client:
        resp = client.post(f"{settings.get('target_agent_url')}/message", json=payload)
        resp.raise_for_status()
        return resp.json()


def run_text_scenario(run_id: str, scenario: Scenario, agent_type: str, turns: int = 3) -> None:
    plan = plan_attack(scenario)
    state = init_turn_state()
    transcript: list[TranscriptEntry] = []
    messages: list[dict] = [{"role": "system", "content": scenario.description}]
    last_response = "Hello"

    for _ in range(turns):
        tester_msg = next_message(scenario, last_response, plan, int(state.get("current_turn") or 0))
        transcript.append(TranscriptEntry(role="tester", content=tester_msg, timestamp=time.time()))
        redis_store.append_transcript(run_id, transcript[-1])

        response = _send_message(agent_type, run_id, tester_msg, messages)
        last_response = response.get("text", "")
        messages = response.get("messages", messages)

        transcript.append(TranscriptEntry(role="target", content=last_response, timestamp=time.time()))
        redis_store.append_transcript(run_id, transcript[-1])

        advance_turn(state)

    grading = grade_transcript_comprehensive(scenario, transcript)
    redis_store.save_grading(run_id, grading.model_dump())


def run_text(run_id: str, scenario_ids: list[str], agent_type: str) -> None:
    scenarios = [s for s in redis_store.list_scenarios() if s.scenario_id in scenario_ids]
    for scenario in scenarios:
        run_text_scenario(run_id, scenario, agent_type)
