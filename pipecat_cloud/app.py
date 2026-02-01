from __future__ import annotations

import asyncio
import json
import os
import time

from pipecatcloud.agent import DailySessionArguments

from ai_health_board.agents.server import app, handle_session_args


async def bot(args: DailySessionArguments):
    return await handle_session_args(args)


def _args_from_env() -> DailySessionArguments:
    body = {}
    raw_body = os.getenv("PIPECAT_BODY") or os.getenv("PIPECAT_DATA")
    if raw_body:
        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError:
            body = {}
    return DailySessionArguments(
        session_id=os.getenv("SESSION_ID") or f"session_{int(time.time())}",
        room_url=os.getenv("DAILY_ROOM_URL", ""),
        token=os.getenv("DAILY_TOKEN") or os.getenv("DAILY_ROOM_TOKEN"),
        body=body,
    )


if __name__ == "__main__":
    room_url = os.getenv("DAILY_ROOM_URL")
    if room_url:
        raw_body = os.getenv("PIPECAT_BODY") or os.getenv("PIPECAT_DATA")
        print(
            f"[pipecat_cloud] direct mode: DAILY_ROOM_URL set={bool(room_url)} "
            f"PIPECAT_BODY bytes={len(raw_body) if raw_body else 0}"
        )
        asyncio.run(handle_session_args(_args_from_env()))
    else:
        import uvicorn

        uvicorn.run(
            app,
            host=os.getenv("PIPECAT_HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", os.getenv("PIPECAT_PORT", "7860"))),
            log_level="info",
        )
