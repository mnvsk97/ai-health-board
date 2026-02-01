from __future__ import annotations

import asyncio
import time
import uuid
from typing import Callable

import httpx
from loguru import logger

from .config import load_settings
from .grader_agent import grade_transcript_comprehensive
from .models import BatchRun, Run, Scenario, ScenarioResult, TranscriptEntry
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


# =============================================================================
# Async Parallel Execution
# =============================================================================


async def run_text_scenario_async(
    run_id: str,
    scenario: Scenario,
    agent_type: str,
    turns: int = 3,
    cancel_event: asyncio.Event | None = None,
) -> ScenarioResult:
    """Run a single text scenario asynchronously.

    Args:
        run_id: Unique run identifier.
        scenario: Scenario to execute.
        agent_type: Type of agent to test.
        turns: Number of conversation turns.
        cancel_event: Optional event to signal cancellation.

    Returns:
        ScenarioResult with execution outcome.
    """
    start_time = time.time()

    try:
        # Check for cancellation before starting
        if cancel_event and cancel_event.is_set():
            return ScenarioResult(
                run_id=run_id,
                scenario_id=scenario.scenario_id,
                status="canceled",
                started_at=start_time,
                completed_at=time.time(),
            )

        # Run the scenario in a thread pool to not block
        await asyncio.to_thread(
            run_text_scenario, run_id, scenario, agent_type, turns
        )

        return ScenarioResult(
            run_id=run_id,
            scenario_id=scenario.scenario_id,
            status="completed",
            started_at=start_time,
            completed_at=time.time(),
        )

    except Exception as e:
        logger.error(f"Scenario {scenario.scenario_id} failed: {e}")
        return ScenarioResult(
            run_id=run_id,
            scenario_id=scenario.scenario_id,
            status="failed",
            error=str(e),
            started_at=start_time,
            completed_at=time.time(),
        )


async def run_text_parallel(
    batch_id: str,
    scenario_ids: list[str],
    agent_type: str,
    concurrency: int = 10,
    turns: int = 3,
    progress_callback: Callable[[str, ScenarioResult], None] | None = None,
) -> list[ScenarioResult]:
    """Run multiple scenarios in parallel with concurrency control.

    Args:
        batch_id: Batch identifier for tracking.
        scenario_ids: List of scenario IDs to run.
        agent_type: Type of agent to test.
        concurrency: Maximum number of concurrent executions.
        turns: Number of conversation turns per scenario.
        progress_callback: Optional callback after each scenario completes.

    Returns:
        List of ScenarioResult objects.
    """
    semaphore = asyncio.Semaphore(concurrency)
    cancel_event = asyncio.Event()

    # Load all scenarios
    all_scenarios = redis_store.list_scenarios()
    scenario_map = {s.scenario_id: s for s in all_scenarios}
    scenarios = [scenario_map[sid] for sid in scenario_ids if sid in scenario_map]

    if not scenarios:
        logger.warning(f"No valid scenarios found for batch {batch_id}")
        return []

    logger.info(f"Starting batch {batch_id} with {len(scenarios)} scenarios, concurrency={concurrency}")

    async def run_with_semaphore(scenario: Scenario) -> ScenarioResult:
        async with semaphore:
            # Check cancellation before each scenario
            if redis_store.is_batch_canceled(batch_id):
                cancel_event.set()

            # Generate unique run ID for this scenario
            run_id = f"run_{uuid.uuid4().hex[:10]}"

            # Create run record
            run = Run(
                run_id=run_id,
                status="pending",
                scenario_ids=[scenario.scenario_id],
                mode="text_text",
                started_at=time.time(),
                updated_at=time.time(),
            )
            redis_store.create_run(run)

            # Update run status to running
            run.status = "running"
            redis_store.update_run(run)

            # Execute scenario
            result = await run_text_scenario_async(
                run_id=run_id,
                scenario=scenario,
                agent_type=agent_type,
                turns=turns,
                cancel_event=cancel_event,
            )

            # Update run status based on result
            run.status = result.status
            run.updated_at = time.time()
            redis_store.update_run(run)

            # Call progress callback if provided
            if progress_callback:
                try:
                    progress_callback(batch_id, result)
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}")

            return result

    # Execute all scenarios with controlled concurrency
    results = await asyncio.gather(
        *[run_with_semaphore(s) for s in scenarios],
        return_exceptions=True,
    )

    # Convert exceptions to failed results
    final_results: list[ScenarioResult] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            final_results.append(
                ScenarioResult(
                    run_id=f"run_error_{i}",
                    scenario_id=scenarios[i].scenario_id if i < len(scenarios) else "unknown",
                    status="failed",
                    error=str(result),
                    started_at=time.time(),
                    completed_at=time.time(),
                )
            )
        else:
            final_results.append(result)

    return final_results


async def execute_batch_run(batch_id: str) -> None:
    """Execute a batch run asynchronously.

    This function is meant to be spawned as a background task.
    It updates the batch status and counts as scenarios complete.

    Args:
        batch_id: Batch identifier.
    """
    batch = redis_store.get_batch_run(batch_id)
    if not batch:
        logger.error(f"Batch {batch_id} not found")
        return

    # Update status to running
    batch.status = "running"
    batch.started_at = time.time()
    redis_store.update_batch_run(batch)

    def on_progress(bid: str, result: ScenarioResult) -> None:
        """Update batch progress after each scenario."""
        b = redis_store.get_batch_run(bid)
        if not b:
            return

        b.child_run_ids.append(result.run_id)

        if result.status == "completed":
            b.completed_count += 1
        elif result.status == "failed":
            b.failed_count += 1
        elif result.status == "canceled":
            b.canceled_count += 1

        redis_store.update_batch_run(b)

    try:
        results = await run_text_parallel(
            batch_id=batch_id,
            scenario_ids=batch.scenario_ids,
            agent_type=batch.agent_type,
            concurrency=batch.concurrency,
            turns=batch.turns,
            progress_callback=on_progress,
        )

        # Determine final status
        batch = redis_store.get_batch_run(batch_id)
        if not batch:
            return

        if redis_store.is_batch_canceled(batch_id):
            batch.status = "canceled"
        elif batch.failed_count > 0 and batch.completed_count == 0:
            batch.status = "failed"
        else:
            batch.status = "completed"

        batch.completed_at = time.time()
        redis_store.update_batch_run(batch)
        redis_store.clear_batch_cancel_flag(batch_id)

        logger.info(
            f"Batch {batch_id} finished: "
            f"{batch.completed_count} completed, "
            f"{batch.failed_count} failed, "
            f"{batch.canceled_count} canceled"
        )

    except Exception as e:
        logger.error(f"Batch {batch_id} execution failed: {e}")
        batch = redis_store.get_batch_run(batch_id)
        if batch:
            batch.status = "failed"
            batch.completed_at = time.time()
            redis_store.update_batch_run(batch)
