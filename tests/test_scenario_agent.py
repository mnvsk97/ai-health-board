from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from ai_health_board import redis_store
from ai_health_board.agents.scenario_agent import build_scenario_workflow_agent


pytest.importorskip("google.adk")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_scenario_agent_runs_pipeline(tmp_path: Path) -> None:
    if shutil.which("node") is None:
        pytest.skip("node is required for Stagehand JS integration")

    run_id = f"test_run_{int(time.time())}"
    bench_path = "data/healthbench_oss_eval_500.jsonl"

    guideline_path = tmp_path / "guidelines.json"
    subprocess.run(
        [
            "node",
            "scripts/stagehand_extract.mjs",
            "--url",
            "https://www.cdc.gov/flu/symptoms/index.html",
            "--out",
            str(guideline_path),
        ],
        check=True,
    )
    guideline_data = json.loads(guideline_path.read_text(encoding="utf-8"))
    assert isinstance(guideline_data, list)

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="scenario_pipeline",
        user_id="test",
        session_id=run_id,
        state={
            "run_id": run_id,
            "bench_path": bench_path,
            "bench_limit": 2,
            "input_guidelines": guideline_data,
        },
    )

    runner = Runner(
        agent=build_scenario_workflow_agent(),
        app_name="scenario_pipeline",
        session_service=session_service,
    )

    async for _event in runner.run_async(
        session_id=run_id,
        user_id="test",
        new_message=types.Content(parts=[types.Part(text="Run scenario pipeline")]),
    ):
        pass

    checkpoint = redis_store.restore_checkpoint(run_id) or {}
    assert checkpoint.get("stage") == "scenarios_published"
    assert len(checkpoint.get("scenario_ids", [])) == 3
