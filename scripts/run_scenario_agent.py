#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from ai_health_board import redis_store
from ai_health_board.agents.scenario_agent import build_scenario_workflow_agent


APP_NAME = "scenario_pipeline"


def _load_guidelines(path: str | None) -> list[dict] | None:
    if not path:
        return None
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Guidelines JSON must be a list")
    return data


async def _run_pipeline(args: argparse.Namespace) -> None:
    run_id = args.run_id or f"sc_run_{int(time.time())}"
    initial_state = {
        "run_id": run_id,
        "bench_path": args.bench,
        "bench_limit": args.limit,
        "dry_run": args.dry_run,
    }
    guidelines = _load_guidelines(args.guidelines)
    if guidelines is not None:
        initial_state["input_guidelines"] = guidelines

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME,
        user_id="demo",
        session_id=run_id,
        state=initial_state,
    )

    runner = Runner(
        agent=build_scenario_workflow_agent(),
        app_name=APP_NAME,
        session_service=session_service,
    )

    async for _event in runner.run_async(
        session_id=run_id,
        user_id="demo",
        new_message=types.Content(parts=[types.Part(text="Run scenario pipeline")]),
    ):
        pass

    checkpoint = redis_store.restore_checkpoint(run_id) or {}
    scenario_ids = checkpoint.get("scenario_ids", [])
    print(f"Run complete: {run_id}")
    print(f"Scenarios published: {len(scenario_ids)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the scenario generation agent")
    parser.add_argument(
        "--bench",
        type=str,
        default="data/healthbench_oss_eval_500.jsonl",
        help="Path to the HealthBench JSONL subset",
    )
    parser.add_argument(
        "--guidelines",
        type=str,
        default=None,
        help="Path to a JSON file containing extracted guidelines",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Maximum number of HealthBench items to load",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Optional run id for checkpointing",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not save scenarios to Redis",
    )
    args = parser.parse_args()

    asyncio.run(_run_pipeline(args))


if __name__ == "__main__":
    main()
