#!/usr/bin/env python
"""Show the current status of the self-improvement system.

This displays:
1. Prompt registry status (usage, success rates)
2. Attack memory statistics
3. Pending improvements
4. Recent Weave traces

Usage:
    python scripts/improvement_status.py
"""
from __future__ import annotations

import sys
from datetime import datetime


def main():
    print("=" * 60)
    print("AI Health Board - Self-Improvement System Status")
    print(f"Generated: {datetime.now().isoformat()}")
    print("=" * 60)

    # 1. Prompt Registry Status
    print("\n## Prompt Registry\n")

    from ai_health_board.improvement import get_registry

    registry = get_registry()
    prompts = registry.list_prompts()

    total_usage = sum(p.get("usage_count", 0) for p in prompts)
    prompts_with_data = [p for p in prompts if p.get("usage_count", 0) >= 10]

    print(f"Total prompts: {len(prompts)}")
    print(f"Total usage across all prompts: {total_usage}")
    print(f"Prompts with sufficient data (10+): {len(prompts_with_data)}")

    # Group by agent type
    tester_prompts = [p for p in prompts if p["prompt_id"].startswith("tester.")]
    grader_prompts = [p for p in prompts if p["prompt_id"].startswith("grader.")]

    print(f"\nTester prompts: {len(tester_prompts)}")
    for p in sorted(tester_prompts, key=lambda x: x["prompt_id"]):
        usage = p.get("usage_count", 0)
        success = p.get("success_rate", 0)
        print(f"  {p['prompt_id']}: {usage} uses, {success:.0%} success")

    print(f"\nGrader prompts: {len(grader_prompts)}")
    for p in sorted(grader_prompts, key=lambda x: x["prompt_id"]):
        usage = p.get("usage_count", 0)
        success = p.get("success_rate", 0)
        print(f"  {p['prompt_id']}: {usage} uses, {success:.0%} success")

    # 2. Prompts needing improvement
    print("\n## Improvement Candidates\n")

    from ai_health_board.improvement import analyze_prompt_performance

    candidates = []
    for p in prompts:
        analysis = analyze_prompt_performance(p["prompt_id"], registry)
        if analysis.get("needs_improvement"):
            candidates.append((p["prompt_id"], analysis))

    if candidates:
        for pid, analysis in candidates:
            print(f"  {pid}:")
            print(f"    Reason: {analysis.get('reason')}")
            print(f"    Success rate: {analysis.get('success_rate', 0):.1%}")
            print(f"    Avg score: {analysis.get('avg_score', 0):.2f}")
    else:
        print("  No prompts currently need improvement")
        print("  (Either performing well or need more usage data)")

    # 3. Attack Memory Status
    print("\n## Attack Memory\n")

    from ai_health_board import redis_store

    try:
        # Get vector effectiveness rates
        from ai_health_board.tester_agent import DEFAULT_VECTORS

        print("Attack vector effectiveness:")
        for vector in DEFAULT_VECTORS:
            rate = redis_store.get_vector_rate(vector)
            print(f"  {vector}: {rate:.1%}")
    except Exception as e:
        print(f"  Could not load attack memory: {e}")

    # 4. Recommendations
    print("\n## Recommendations\n")

    if total_usage < 50:
        print("  1. Run more tests to gather data")
        print("     Command: python scripts/generate_test_traces.py --count 10")
    elif len(prompts_with_data) < 5:
        print("  1. Continue running tests - some prompts need more data")
    else:
        print("  1. Run improvement cycle to analyze and create variants")
        print("     Command: python scripts/run_improvement_cycle.py")

    if not candidates and len(prompts_with_data) > 5:
        print("  2. System is healthy - prompts are performing well")
    elif candidates:
        print(f"  2. {len(candidates)} prompts flagged for improvement")

    print("\n## Cron Schedule Recommendations\n")
    print("  # Generate test traces every 6 hours")
    print("  0 */6 * * * cd /path/to/project && .venv/bin/python scripts/generate_test_traces.py --count 5")
    print("")
    print("  # Run improvement cycle daily at 2am")
    print("  0 2 * * * cd /path/to/project && .venv/bin/python scripts/run_improvement_cycle.py")
    print("")
    print("  # Check status weekly")
    print("  0 9 * * 1 cd /path/to/project && .venv/bin/python scripts/improvement_status.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())
