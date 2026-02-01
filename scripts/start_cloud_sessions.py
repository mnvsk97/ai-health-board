#!/usr/bin/env python3
"""Start Pipecat Cloud target + tester sessions via REST API.

This uses the public start endpoint to ensure Daily room/token and payload body
are passed deterministically to the bots.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

import httpx


API_BASE = os.getenv("PIPECAT_API_BASE", "https://api.pipecat.daily.co/v1/public")


def _env(name: str, default: str | None = None) -> str:
    value = os.getenv(name)
    if value:
        return value
    if default is not None:
        return default
    raise RuntimeError(f"Missing required env var: {name}")


def _post_start(agent_name: str, api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{API_BASE}/{agent_name}/start"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=30) as client:
        response = client.post(url, headers=headers, json=payload)
    if response.status_code >= 400:
        raise RuntimeError(f"Start failed ({response.status_code}): {response.text}")
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario-id", required=True)
    parser.add_argument("--run-id", default=f"run_{int(time.time())}")
    parser.add_argument("--max-turns", type=int, default=3)
    parser.add_argument("--target-agent", default=os.getenv("PIPECAT_TARGET_AGENT", "preclinical-intake-agent"))
    parser.add_argument("--tester-agent", default=os.getenv("PIPECAT_TESTER_AGENT", "preclinical-tester-agent"))
    args = parser.parse_args()

    api_key = _env("PIPECAT_CLOUD_API_KEY")

    # 1) Start target agent + create Daily room
    target_payload = {
        "createDailyRoom": True,
        "transport": "daily",
        "body": {
            "agent_type": "intake",
            "run_id": args.run_id,
        },
    }
    target = _post_start(args.target_agent, api_key, target_payload)
    room_url = target.get("dailyRoom")
    token = target.get("dailyToken")
    if not room_url or not token:
        raise RuntimeError(f"Target start did not return dailyRoom/dailyToken: {json.dumps(target)}")

    # 2) Start tester agent in same room
    tester_payload = {
        "createDailyRoom": False,
        "transport": "daily",
        "body": {
            "agent_type": "tester",
            "scenario_id": args.scenario_id,
            "run_id": args.run_id,
            "room_url": room_url,
            "token": token,
            "max_turns": args.max_turns,
        },
    }
    tester = _post_start(args.tester_agent, api_key, tester_payload)

    print("Started sessions:")
    print(f"- target_agent: {args.target_agent}")
    print(f"- tester_agent: {args.tester_agent}")
    print(f"- run_id: {args.run_id}")
    print(f"- room_url: {room_url}")
    print(f"- target_session_id: {target.get('sessionId')}")
    print(f"- tester_session_id: {tester.get('sessionId')}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}")
        raise
