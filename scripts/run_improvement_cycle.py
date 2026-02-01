#!/usr/bin/env python
"""Run the self-improvement cycle.

This script should be scheduled as a cron job to:
1. Analyze prompt performance
2. Generate variants for underperforming prompts
3. Evaluate and promote winning variants

Recommended schedule: Daily or after every 50+ test runs

Usage:
    python scripts/run_improvement_cycle.py [--dry-run] [--min-usage N]

Cron example (daily at 2am):
    0 2 * * * cd /path/to/ai-health-board && .venv/bin/python scripts/run_improvement_cycle.py
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime

from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Run self-improvement cycle")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze only, don't create variants",
    )
    parser.add_argument(
        "--min-usage",
        type=int,
        default=20,
        help="Minimum usage count before analyzing (default: 20)",
    )
    parser.add_argument(
        "--min-promotion",
        type=int,
        default=30,
        help="Minimum samples before promoting variant (default: 30)",
    )
    args = parser.parse_args()

    logger.info(f"Starting improvement cycle at {datetime.now().isoformat()}")

    from ai_health_board.improvement import (
        get_registry,
        analyze_prompt_performance,
        run_validated_improvement_cycle,
    )

    registry = get_registry()
    prompts = registry.list_prompts()

    logger.info(f"Analyzing {len(prompts)} prompts")

    # First, show current status
    print("\n=== Current Prompt Performance ===\n")
    for p in sorted(prompts, key=lambda x: x.get("prompt_id", "")):
        pid = p.get("prompt_id", "unknown")
        usage = p.get("usage_count", 0)
        success_rate = p.get("success_rate", 0)
        avg_score = p.get("avg_score", 0)

        status = "OK"
        if usage >= args.min_usage:
            if success_rate < 0.7 or avg_score < 0.6:
                status = "NEEDS IMPROVEMENT"
        else:
            status = f"need {args.min_usage - usage} more samples"

        print(f"  {pid}:")
        print(f"    usage={usage}, success={success_rate:.1%}, avg_score={avg_score:.2f}")
        print(f"    status: {status}")
        print()

    if args.dry_run:
        print("\n[DRY RUN] Would analyze and create variants for underperforming prompts")
        print("Run without --dry-run to execute improvements")
        return 0

    # Run the improvement cycle
    print("\n=== Running Improvement Cycle ===\n")
    result = run_validated_improvement_cycle(
        min_usage_for_improvement=args.min_usage,
        min_usage_for_promotion=args.min_promotion,
    )

    print(f"\nResults:")
    print(f"  Prompts analyzed: {result.prompts_analyzed}")
    print(f"  Variants created: {result.variants_created}")
    print(f"  Variants promoted: {result.variants_promoted}")

    if result.improvements:
        print(f"\nImprovements made:")
        for imp in result.improvements:
            print(f"  - {imp.get('prompt_id')}: {imp.get('action')}")
            if imp.get("expected_improvement"):
                print(f"    Expected: {imp.get('expected_improvement')}")

    logger.info(f"Improvement cycle complete at {datetime.now().isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
