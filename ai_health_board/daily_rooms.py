from __future__ import annotations

import time
from typing import Any

import httpx

from .config import load_settings


def _headers() -> dict[str, str]:
    settings = load_settings()
    api_key = str(settings.get("daily_api_key") or "")
    if not api_key:
        raise ValueError("DAILY_API_KEY is required")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def create_room(expiry_seconds: int = 600) -> dict[str, Any]:
    payload = {
        "properties": {
            "exp": int(time.time()) + expiry_seconds,
            "enable_chat": True,
            "enable_screenshare": False,
            "start_video_off": True,
            "start_audio_off": False,
        }
    }
    with httpx.Client(timeout=15) as client:
        resp = client.post("https://api.daily.co/v1/rooms", headers=_headers(), json=payload)
        resp.raise_for_status()
        return resp.json()


def get_meeting_token(room_name: str, owner: bool = False, expiry_seconds: int = 600) -> str:
    payload = {
        "properties": {
            "room_name": room_name,
            "is_owner": owner,
            "exp": int(time.time()) + expiry_seconds,
        }
    }
    with httpx.Client(timeout=15) as client:
        resp = client.post("https://api.daily.co/v1/meeting-tokens", headers=_headers(), json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["token"]


def delete_room(room_name: str) -> None:
    with httpx.Client(timeout=10) as client:
        resp = client.delete(f"https://api.daily.co/v1/rooms/{room_name}", headers=_headers())
        if resp.status_code not in (200, 404):
            resp.raise_for_status()
