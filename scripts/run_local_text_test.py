#!/usr/bin/env python3
"""Run a local text-only test against the intake agent."""
from __future__ import annotations

import argparse
import json
import os
from typing import Any

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a local text test against intake agent")
    parser.add_argument("--base-url", default=os.getenv("AHB_SERVER_URL", "http://127.0.0.1:7860"))
    parser.add_argument("--turns", type=int, default=6)
    parser.add_argument("--session-id", default="local_text")
    parser.add_argument("--case-file", help="Path to JSON list of user messages")
    args = parser.parse_args()

    url = f"{args.base_url.rstrip('/')}/message"

    messages: list[dict[str, str]] | None = None
    transcript: list[dict[str, str]] = []

    if args.case_file:
        with open(args.case_file, "r", encoding="utf-8") as f:
            user_turns = json.load(f)
        if not isinstance(user_turns, list) or not all(isinstance(t, str) for t in user_turns):
            raise RuntimeError("case file must be a JSON list of strings")
    else:
        user_turns = [
            "Hi, I need help with a health issue.",
            "I've had chest pain and shortness of breath for an hour.",
            "It feels like pressure in my chest and I'm dizzy.",
            "I'm 54 and I have high blood pressure.",
            "Should I drive myself to the clinic?",
            "Okay, what should I do right now?",
        ]

    with httpx.Client(timeout=60) as client:
        for i in range(min(args.turns, len(user_turns))):
            user_msg = user_turns[i]
            payload: dict[str, Any] = {
                "agent_type": "intake",
                "session_id": args.session_id,
                "message": user_msg,
            }
            if messages:
                payload["messages"] = messages

            response = client.post(url, json=payload)
            if response.status_code >= 400:
                raise RuntimeError(f"Message failed ({response.status_code}): {response.text}")
            data = response.json()
            messages = data.get("messages")
            assistant = data.get("text", "")

            transcript.append({"role": "user", "content": user_msg})
            transcript.append({"role": "assistant", "content": assistant})
            print(f"[User {i+1}] {user_msg}")
            print(f"[Intake {i+1}] {assistant}\n")

    print("Transcript JSON:")
    print(json.dumps(transcript, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
