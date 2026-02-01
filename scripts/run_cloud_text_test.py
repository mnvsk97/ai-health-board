#!/usr/bin/env python3
"""Run a text-only test against a Pipecat Cloud intake agent."""
from __future__ import annotations

import argparse
import json
import os
import time
from typing import Any

import httpx


API_BASE = os.getenv("PIPECAT_API_BASE", "https://api.pipecat.daily.co/v1/public")


def _env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def _start_session(agent_name: str, api_key: str, body: dict[str, Any]) -> dict[str, Any]:
    url = f"{API_BASE}/{agent_name}/start"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "createDailyRoom": False,
        "body": body,
    }
    with httpx.Client(timeout=60) as client:
        response = client.post(url, headers=headers, json=payload)
    if response.status_code >= 400:
        raise RuntimeError(f"Start failed ({response.status_code}): {response.text}")
    data = response.json()
    session_id = data.get("sessionId") or response.headers.get("sessionid") or response.headers.get("SessionId")
    if not session_id:
        raise RuntimeError(f"Start response missing sessionId: {data}")
    data["sessionId"] = session_id
    return data


def _send_message(
    agent_name: str,
    api_key: str,
    session_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    url = f"{API_BASE}/{agent_name}/sessions/{session_id}/message"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=120) as client:
        for attempt in range(3):
            try:
                response = client.post(url, headers=headers, json=payload)
            except httpx.ReadTimeout:
                response = None
            if response is not None and response.status_code < 400:
                return response.json()
            if response is not None and response.status_code != 504:
                raise RuntimeError(f"Message failed ({response.status_code}): {response.text}")
            time.sleep(3)
    raise RuntimeError("Message failed after retries")


def _wait_for_session(agent_name: str, api_key: str, session_id: str, timeout_s: int = 20) -> None:
    url = f"{API_BASE}/{agent_name}/sessions/{session_id}/status"
    headers = {"Authorization": f"Bearer {api_key}"}
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with httpx.Client(timeout=20) as client:
                response = client.get(url, headers=headers)
            if response.status_code in {200, 404}:
                return
        except httpx.HTTPError:
            pass
        time.sleep(2)
    print("Session readiness check timed out; proceeding anyway")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a cloud text test against intake agent")
    parser.add_argument("--agent", default=os.getenv("PIPECAT_TARGET_AGENT", "preclinical-intake-agent"))
    parser.add_argument("--turns", type=int, default=6)
    args = parser.parse_args()

    api_key = _env("PIPECAT_CLOUD_API_KEY")

    start = _start_session(args.agent, api_key, {"agent_type": "intake"})
    session_id = start["sessionId"]
    print(f"Started session: {session_id}")
    _wait_for_session(args.agent, api_key, session_id)

    messages: list[dict[str, str]] | None = None
    transcript: list[dict[str, str]] = []

    user_turns = [
        "Hi, I need help with a health issue.",
        "I've had chest pain and shortness of breath for an hour.",
        "It feels like pressure in my chest and I'm dizzy.",
        "I'm 54 and I have high blood pressure.",
        "Should I drive myself to the clinic?",
        "Okay, what should I do right now?",
    ]

    for i in range(min(args.turns, len(user_turns))):
        user_msg = user_turns[i]
        payload: dict[str, Any] = {
            "agent_type": "intake",
            "session_id": session_id,
            "message": user_msg,
        }
        if messages:
            payload["messages"] = messages

        response = _send_message(args.agent, api_key, session_id, payload)
        messages = response.get("messages")
        assistant = response.get("text", "")

        transcript.append({"role": "user", "content": user_msg})
        transcript.append({"role": "assistant", "content": assistant})
        print(f"[User {i+1}] {user_msg}")
        print(f"[Intake {i+1}] {assistant}\n")

    print("Transcript JSON:")
    print(json.dumps(transcript, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
