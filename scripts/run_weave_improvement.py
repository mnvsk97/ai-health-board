#!/usr/bin/env python3
"""Run Weave-powered self-improvement cycle.

This script uses Weave's native features (scorers, feedback, call querying)
to analyze test patterns and improve the tester agent.

Usage:
    python scripts/run_weave_improvement.py [--hours 24]
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


def main():
    parser = argparse.ArgumentParser(
        description="Run Weave-powered self-improvement cycle"
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Hours to look back for traces (default: 24)",
    )
    parser.add_argument(
        "--max-technique-improvements",
        type=int,
        default=3,
        help="Max techniques to improve (default: 3)",
    )
    parser.add_argument(
        "--max-boundary-attacks",
        type=int,
        default=2,
        help="Max boundaries to generate attacks for (default: 2)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output",
    )
    args = parser.parse_args()

    from ai_health_board.weave_self_improve import run_weave_improvement_cycle

    logger.info("Starting Weave-powered improvement cycle")
    logger.info(f"  Looking back: {args.hours} hours")

    result = run_weave_improvement_cycle(
        hours=args.hours,
        max_technique_improvements=args.max_technique_improvements,
        max_boundary_attacks=args.max_boundary_attacks,
    )

    print("\n" + "=" * 60)
    print("WEAVE-POWERED IMPROVEMENT CYCLE COMPLETE")
    print("=" * 60)
    print(f"\nStatus: {result['status']}")

    if result["status"] == "completed":
        insights = result.get("insights", {})
        print(f"\nInteractions analyzed: {result.get('interactions_analyzed', 0)}")
        print(f"Average attack effectiveness: {insights.get('avg_effectiveness', 0):.1%}")
        print(f"Violation trigger rate: {insights.get('violation_rate', 0):.1%}")

        print(f"\nTechnique analysis:")
        print(f"  - Effective techniques: {insights.get('effective_techniques', 0)}")
        print(f"  - Underperforming techniques: {insights.get('underperforming_techniques', 0)}")
        print(f"  - Untested boundaries: {insights.get('untested_boundaries', [])}")

        print(f"\nImprovements made:")
        print(f"  - Techniques improved: {len(result.get('technique_improvements', []))}")
        print(f"  - Boundary attacks generated: {len(result.get('boundary_attacks', []))}")

        if args.verbose:
            if result.get("technique_improvements"):
                print("\nTechnique Improvements:")
                for imp in result["technique_improvements"]:
                    print(f"\n  {imp['technique']}:")
                    improvements = imp.get("improvements", {})
                    for p in improvements.get("improved_prompts", [])[:2]:
                        print(f"    - {p['prompt'][:80]}...")
                        print(f"      ({p['improvement']})")
                    if improvements.get("technique_tips"):
                        print(f"    Tips: {improvements['technique_tips']}")

            if result.get("boundary_attacks"):
                print("\nBoundary Attacks Generated:")
                for ba in result["boundary_attacks"]:
                    print(f"\n  {ba['boundary']}:")
                    for attack in ba.get("attacks", [])[:2]:
                        print(f"    - {attack['prompt'][:80]}...")

        if result.get("recommendations"):
            print("\nRecommendations:")
            for rec in result["recommendations"]:
                print(f"  - {rec}")


if __name__ == "__main__":
    main()
