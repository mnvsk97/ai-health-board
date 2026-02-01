#!/usr/bin/env python3
"""Seed HealthBench data with scenarios and attack vectors.

Usage:
    python scripts/seed_healthbench_batch.py --limit 100 --concurrency 5
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import time
from pathlib import Path

from loguru import logger

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_health_board.models import HealthBenchItem, HealthBenchPrompt, RubricCriterion, Scenario
from ai_health_board.scenario_pipeline import generate_scenario_from_bench_item
from ai_health_board import redis_store
from ai_health_board.attack_memory import derive_attacks_from_scenario


def load_healthbench_items(path: str | Path, limit: int = 100) -> list[HealthBenchItem]:
    """Load HealthBench items from a JSONL file.

    Args:
        path: Path to the JSONL file.
        limit: Maximum number of items to load.

    Returns:
        List of HealthBenchItem objects.
    """
    items: list[HealthBenchItem] = []
    path = Path(path)

    if not path.exists():
        logger.error(f"HealthBench file not found: {path}")
        return items

    with open(path, "r") as f:
        for i, line in enumerate(f):
            if i >= limit:
                break
            try:
                data = json.loads(line)
                # Parse prompt list
                prompts = [
                    HealthBenchPrompt(role=p["role"], content=p["content"])
                    for p in data.get("prompt", [])
                ]
                # Parse rubrics
                rubrics = [
                    RubricCriterion(
                        criterion=r["criterion"],
                        points=r.get("points", 5),
                        tags=r.get("tags", []),
                    )
                    for r in data.get("rubrics", [])
                ]
                item = HealthBenchItem(
                    prompt_id=data["prompt_id"],
                    prompt=prompts,
                    rubrics=rubrics,
                    example_tags=data.get("example_tags", []),
                )
                items.append(item)
            except Exception as e:
                logger.warning(f"Failed to parse line {i}: {e}")
                continue

    logger.info(f"Loaded {len(items)} HealthBench items from {path}")
    return items


async def seed_scenario_with_attacks(
    item: HealthBenchItem,
    semaphore: asyncio.Semaphore,
) -> tuple[Scenario | None, int]:
    """Create a scenario and derive attack vectors for it.

    Args:
        item: HealthBench item to convert.
        semaphore: Semaphore for concurrency control.

    Returns:
        Tuple of (Scenario, attack_count) or (None, 0) on failure.
    """
    async with semaphore:
        try:
            # Generate scenario from bench item
            scenario = await asyncio.to_thread(
                generate_scenario_from_bench_item, item
            )

            # Save scenario to Redis
            redis_store.save_scenario(scenario)
            logger.debug(f"Saved scenario: {scenario.scenario_id} - {scenario.title}")

            # Derive attack vectors
            try:
                attacks = await asyncio.to_thread(
                    derive_attacks_from_scenario, scenario
                )
                attack_count = len(attacks) if attacks else 0
                logger.debug(f"Generated {attack_count} attacks for {scenario.scenario_id}")
            except Exception as e:
                logger.warning(f"Failed to derive attacks for {scenario.scenario_id}: {e}")
                attack_count = 0

            return scenario, attack_count

        except Exception as e:
            logger.error(f"Failed to seed scenario for {item.prompt_id}: {e}")
            return None, 0


async def seed_batch(
    items: list[HealthBenchItem],
    concurrency: int = 5,
) -> dict:
    """Seed a batch of HealthBench items with parallel execution.

    Args:
        items: List of HealthBench items to seed.
        concurrency: Number of concurrent tasks.

    Returns:
        Summary dict with counts.
    """
    semaphore = asyncio.Semaphore(concurrency)
    start_time = time.time()

    logger.info(f"Seeding {len(items)} items with concurrency={concurrency}")

    tasks = [
        seed_scenario_with_attacks(item, semaphore)
        for item in items
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    scenarios_created = 0
    total_attacks = 0
    failed = 0

    for result in results:
        if isinstance(result, Exception):
            failed += 1
            logger.error(f"Task failed with exception: {result}")
        elif result[0] is not None:
            scenarios_created += 1
            total_attacks += result[1]
        else:
            failed += 1

    elapsed = time.time() - start_time

    summary = {
        "total_items": len(items),
        "scenarios_created": scenarios_created,
        "total_attacks": total_attacks,
        "failed": failed,
        "elapsed_seconds": round(elapsed, 2),
        "items_per_second": round(len(items) / elapsed, 2) if elapsed > 0 else 0,
    }

    logger.info(f"Seeding complete: {summary}")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Seed HealthBench data")
    parser.add_argument(
        "--path",
        type=str,
        default="data/healthbench_oss_eval_500.jsonl",
        help="Path to HealthBench JSONL file",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of items to seed",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Number of concurrent tasks",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load data but don't save to Redis",
    )

    args = parser.parse_args()

    # Load items
    items = load_healthbench_items(args.path, limit=args.limit)

    if not items:
        logger.error("No items loaded. Exiting.")
        return

    if args.dry_run:
        logger.info(f"Dry run: would seed {len(items)} items")
        for item in items[:5]:
            logger.info(f"  - {item.prompt_id}: {item.example_tags}")
        return

    # Run async seeding
    summary = asyncio.run(seed_batch(items, concurrency=args.concurrency))

    print("\n" + "=" * 50)
    print("Seeding Summary")
    print("=" * 50)
    print(f"Total items:       {summary['total_items']}")
    print(f"Scenarios created: {summary['scenarios_created']}")
    print(f"Attack vectors:    {summary['total_attacks']}")
    print(f"Failed:            {summary['failed']}")
    print(f"Elapsed time:      {summary['elapsed_seconds']}s")
    print(f"Throughput:        {summary['items_per_second']} items/s")
    print("=" * 50)


if __name__ == "__main__":
    main()
