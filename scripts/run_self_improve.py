#!/usr/bin/env python3
"""Run a self-improvement cycle for the tester agent.

This script analyzes recent Weave traces and:
1. Identifies underperforming attack prompts
2. Refines them using LLM-based prompt engineering
3. Generates new attack vectors based on successful patterns
4. Updates strategy overlays for different scenario types

Usage:
    python scripts/run_self_improve.py [--hours 24] [--max-refinements 5]
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from loguru import logger
from ai_health_board.self_improve import (
    run_improvement_cycle,
    fetch_recent_traces,
    analyze_trace,
    aggregate_attack_stats,
)


def main():
    parser = argparse.ArgumentParser(
        description="Run self-improvement cycle for tester agent"
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Hours to look back for traces (default: 24)",
    )
    parser.add_argument(
        "--max-refinements",
        type=int,
        default=5,
        help="Maximum prompts to refine per cycle (default: 5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze without making changes",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output",
    )
    args = parser.parse_args()

    logger.info(f"Starting self-improvement cycle")
    logger.info(f"  Looking back: {args.hours} hours")
    logger.info(f"  Max refinements: {args.max_refinements}")
    logger.info(f"  Dry run: {args.dry_run}")

    if args.dry_run:
        # Just analyze and report
        traces = fetch_recent_traces(hours=args.hours, limit=200)
        logger.info(f"Fetched {len(traces)} traces")

        analyses = []
        for trace in traces:
            analysis = analyze_trace(trace)
            if analysis:
                analyses.append(analysis)
        logger.info(f"Analyzed {len(analyses)} valid traces")

        if analyses:
            stats = aggregate_attack_stats(analyses)
            print("\n" + "=" * 60)
            print("ANALYSIS RESULTS (DRY RUN)")
            print("=" * 60)
            print(f"\nTotal tests analyzed: {stats['total_tests']}")
            print(f"Target pass rate: {stats['pass_rate']:.1%}")
            print(f"Average severity: {stats['avg_severity']:.2f}/4.0")

            print("\nTop effective patterns:")
            for pattern, count in stats.get("top_effective_patterns", [])[:5]:
                print(f"  - ({count}x) {pattern[:80]}...")

            print("\nUnderperforming patterns (candidates for refinement):")
            for item in stats.get("underperforming_categories", [])[:5]:
                print(
                    f"  - {item['prompt_preview'][:60]}... "
                    f"({item['effective_rate']:.0%} effective, {item['total_uses']} uses)"
                )

            if args.verbose:
                print("\n\nDetailed analyses:")
                for analysis in analyses[:5]:
                    print(f"\n--- Run: {analysis.run_id} ---")
                    print(f"  Scenario: {analysis.scenario_id}")
                    print(f"  Tags: {analysis.scenario_tags}")
                    print(f"  Passed: {analysis.passed}")
                    print(f"  Severity: {analysis.severity}")
                    print(f"  Effective attacks: {len(analysis.effective_attacks)}")
                    print(f"  Ineffective attacks: {len(analysis.ineffective_attacks)}")
        else:
            print("\nNo valid traces found for analysis")
        return

    # Full improvement cycle
    result = run_improvement_cycle(
        hours=args.hours,
        max_refinements=args.max_refinements,
    )

    print("\n" + "=" * 60)
    print("SELF-IMPROVEMENT CYCLE COMPLETE")
    print("=" * 60)
    print(f"\nStatus: {result['status']}")

    if result["status"] == "completed":
        stats = result.get("stats", {})
        print(f"\nTraces analyzed: {result['traces_analyzed']}")
        print(f"Target pass rate: {stats.get('pass_rate', 0):.1%}")

        print(f"\nImprovements made:")
        print(f"  - Prompts refined: {result['refinements_made']}")
        print(f"  - New attacks generated: {result['new_attacks_generated']}")
        print(f"  - Strategy overlays updated: {result['overlays_updated']}")

        if args.verbose and result.get("refinements"):
            print("\nRefinements:")
            for ref in result["refinements"]:
                print(f"\n  Category: {ref['category']}")
                print(f"  Original: {ref['original_prompt'][:100]}...")
                print(f"  Improved: {ref['improved_prompt'][:100]}...")
                print(f"  Reasoning: {ref['reasoning']}")

        if args.verbose and result.get("new_attacks"):
            print("\nNew attacks:")
            for attack in result["new_attacks"]:
                print(f"\n  Category: {attack['category']}")
                print(f"  Prompt: {attack['prompt'][:100]}...")
                print(f"  Tags: {attack.get('tags', [])}")


if __name__ == "__main__":
    main()
