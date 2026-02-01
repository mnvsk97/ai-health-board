"""Placeholder for Pipecat integration.

This module will be expanded to:
- create Daily rooms and tokens
- run Pipecat tester agent against target agent
- support text/text, text/voice, voice/voice modes
"""
from __future__ import annotations

def create_room(room_name: str, daily_domain: str) -> dict[str, str]:
    # TODO: Use Daily API to create room + token
    room_url = f"https://{daily_domain}.daily.co/{room_name}"
    return {"room_url": room_url, "token": ""}
