#!/usr/bin/env python3
"""
E2E Demo Script: Run multiple test scenarios against the local intake agent.

This script demonstrates the full testing pipeline:
1. Pick random scenarios from Redis
2. Run tester agent conversations against local intake agent
3. Save transcripts to Redis
4. Run 6-stage grading pipeline
5. Display results summary

Usage:
    python scripts/run_e2e_demo.py --count 10 --turns 10
    python scripts/run_e2e_demo.py --scenario sc_abc123 --turns 5
"""
from __future__ import annotations

import argparse
import asyncio
import random
import sys
import time
import uuid

from loguru import logger

# Add project root to path
sys.path.insert(0, str(__file__).rsplit("/scripts", 1)[0])

from ai_health_board import redis_store
from ai_health_board.config import load_settings
from ai_health_board.models import Run, Scenario
from ai_health_board.run_orchestrator import run_text_scenario


def get_random_scenarios(count: int) -> list[Scenario]:
    """Get random scenarios from Redis."""
    all_scenarios = redis_store.list_scenarios()
    if not all_scenarios:
        logger.error("No scenarios found in Redis. Seed some scenarios first.")
        return []

    if count >= len(all_scenarios):
        return all_scenarios

    return random.sample(all_scenarios, count)


def get_scenario_by_id(scenario_id: str) -> Scenario | None:
    """Get a specific scenario by ID."""
    return redis_store.get_scenario(scenario_id)


def run_single_test(
    scenario: Scenario,
    agent_type: str,
    turns: int,
    index: int,
    total: int,
) -> dict:
    """Run a single E2E test and return results.

    Returns:
        dict with keys: run_id, scenario_id, status, score, error
    """
    run_id = f"run_{uuid.uuid4().hex[:10]}"

    print(f"\n[{index}/{total}] Scenario: {scenario.scenario_id}")
    print(f"    Title: {scenario.title[:60]}{'...' if len(scenario.title) > 60 else ''}")
    print(f"    Running {turns} turns...", end=" ", flush=True)

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

    start_time = time.time()

    try:
        # Update status to running
        run.status = "running"
        redis_store.update_run(run)

        # Execute the scenario
        run_text_scenario(run_id, scenario, agent_type, turns)

        # Get grading results
        grading = redis_store.get_grading(run_id)
        elapsed = time.time() - start_time

        # Calculate overall score from evaluations
        score = 0
        max_score = 0
        if grading and "evaluations" in grading:
            for eval_item in grading.get("evaluations", []):
                score += eval_item.get("score", 0)
                max_score += eval_item.get("max_score", 5)

        score_pct = (score / max_score * 100) if max_score > 0 else 0

        # Determine pass/fail based on severity
        severity = grading.get("severity", "low") if grading else "unknown"
        passed = severity in ("low", "medium")
        status_str = "PASS" if passed else "FAIL"

        print(f"Done ({elapsed:.1f}s)")
        print(f"    → Transcript: {turns} turns captured")
        print(f"    → Grading: {status_str} (score: {score}/{max_score}, {score_pct:.0f}%)")
        print(f"    → Severity: {severity}")

        # Update run status
        run.status = "completed"
        redis_store.update_run(run)

        return {
            "run_id": run_id,
            "scenario_id": scenario.scenario_id,
            "status": "passed" if passed else "failed",
            "score": score,
            "max_score": max_score,
            "score_pct": score_pct,
            "severity": severity,
            "elapsed": elapsed,
            "error": None,
        }

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"Error ({elapsed:.1f}s)")
        print(f"    → Error: {str(e)[:80]}")
        logger.exception(f"Failed to run scenario {scenario.scenario_id}")

        # Update run status
        run.status = "failed"
        redis_store.update_run(run)

        return {
            "run_id": run_id,
            "scenario_id": scenario.scenario_id,
            "status": "error",
            "score": 0,
            "max_score": 0,
            "score_pct": 0,
            "severity": "unknown",
            "elapsed": elapsed,
            "error": str(e),
        }


def print_summary(results: list[dict]) -> None:
    """Print summary of all test results."""
    passed = sum(1 for r in results if r["status"] == "passed")
    failed = sum(1 for r in results if r["status"] == "failed")
    errors = sum(1 for r in results if r["status"] == "error")

    total_score = sum(r["score"] for r in results)
    total_max = sum(r["max_score"] for r in results)
    avg_score = (total_score / total_max * 100) if total_max > 0 else 0

    total_time = sum(r["elapsed"] for r in results)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total tests:    {len(results)}")
    print(f"  Passed:         {passed}")
    print(f"  Failed:         {failed}")
    print(f"  Errors:         {errors}")
    print(f"  Average Score:  {avg_score:.1f}%")
    print(f"  Total Time:     {total_time:.1f}s")
    print("=" * 60)

    # Show failed/error details
    failures = [r for r in results if r["status"] in ("failed", "error")]
    if failures:
        print("\nFailed/Error Details:")
        for r in failures:
            print(f"  - {r['scenario_id']}: {r['status']} ({r['severity']})")
            if r["error"]:
                print(f"      Error: {r['error'][:60]}")


def verify_agent_connection(agent_url: str) -> bool:
    """Verify the target agent is reachable."""
    import httpx

    try:
        with httpx.Client(timeout=5) as client:
            # Try health endpoint first
            try:
                resp = client.get(f"{agent_url}/health")
                if resp.status_code == 200:
                    return True
            except httpx.HTTPError:
                pass

            # Try root endpoint
            try:
                resp = client.get(agent_url)
                return resp.status_code in (200, 404, 405)
            except httpx.HTTPError:
                pass

        return False
    except Exception as e:
        logger.warning(f"Agent connection check failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Run E2E tests against the local intake agent"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of scenarios to test (default: 10)",
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=10,
        help="Number of conversation turns per scenario (default: 10)",
    )
    parser.add_argument(
        "--agent-type",
        type=str,
        default="intake",
        help="Type of agent to test (default: intake)",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        help="Specific scenario ID to test (overrides --count)",
    )
    parser.add_argument(
        "--skip-connection-check",
        action="store_true",
        help="Skip verifying agent connection before running",
    )

    args = parser.parse_args()

    # Load settings and show config
    settings = load_settings()
    agent_url = settings.get("target_agent_url")

    print("=" * 60)
    print("E2E DEMO: Testing Intake Agent")
    print("=" * 60)
    print(f"Target Agent URL: {agent_url}")
    print(f"Agent Type:       {args.agent_type}")
    print(f"Turns per test:   {args.turns}")

    # Verify agent connection
    if not args.skip_connection_check:
        print("\nVerifying agent connection...", end=" ", flush=True)
        if not verify_agent_connection(agent_url):
            print("FAILED")
            print(f"\nCould not connect to agent at {agent_url}")
            print("Make sure the agent server is running:")
            print("  python -m ai_health_board.agents.server")
            sys.exit(1)
        print("OK")

    # Get scenarios
    if args.scenario:
        scenario = get_scenario_by_id(args.scenario)
        if not scenario:
            print(f"\nScenario {args.scenario} not found in Redis")
            sys.exit(1)
        scenarios = [scenario]
        print(f"\nRunning 1 specific scenario: {args.scenario}")
    else:
        scenarios = get_random_scenarios(args.count)
        if not scenarios:
            print("\nNo scenarios available. Seed scenarios first:")
            print("  python scripts/seed_scenario.py")
            print("  python scripts/seed_healthbench_batch.py")
            sys.exit(1)
        print(f"\nRunning {len(scenarios)} random scenarios")

    print("-" * 60)

    # Run all tests
    results = []
    for i, scenario in enumerate(scenarios, 1):
        result = run_single_test(
            scenario=scenario,
            agent_type=args.agent_type,
            turns=args.turns,
            index=i,
            total=len(scenarios),
        )
        results.append(result)

    # Print summary
    print_summary(results)

    # Exit with appropriate code
    failed = sum(1 for r in results if r["status"] != "passed")
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
