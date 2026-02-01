#!/usr/bin/env python
"""Sync Weave scores back into the prompt registry.

This closes the improvement loop by:
1. Querying recent scored calls from Weave
2. Extracting scores attached via apply_scorer()
3. Updating prompt registry with real performance data

This should run BEFORE run_improvement_cycle.py

Usage:
    python scripts/sync_weave_scores.py [--hours N] [--dry-run]

Cron example (run before improvement cycle):
    0 1 * * * cd /path/to/project && .venv/bin/python scripts/sync_weave_scores.py
    0 2 * * * cd /path/to/project && .venv/bin/python scripts/run_improvement_cycle.py
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from typing import Any

from loguru import logger


# Map Weave op names to prompt registry IDs
OP_TO_PROMPT_MAP = {
    "tester.generate_attack": "tester.system",
    "tester.next_message": "tester.system",
    "grading.scenario_context": "grader.scenario_context.system",
    "grading.turn_analysis": "grader.turn_analysis.system",
    "grading.rubric_evaluation": "grader.rubric_evaluation.system",
    "grading.safety_audit": "grader.safety_audit.system",
    "grading.quality_assessment": "grader.quality_assessment.system",
    "grading.compliance_audit": "grader.compliance_audit.system",
    "grading.severity_determination": "grader.severity_determination.system",
}


def query_recent_calls(hours: int = 24) -> list[dict[str, Any]]:
    """Query recent calls with scores from Weave."""
    import weave
    from weave.trace.weave_client import get_weave_client

    client = get_weave_client()
    if not client:
        logger.warning("No Weave client available")
        return []

    # Calculate time filter
    since = datetime.utcnow() - timedelta(hours=hours)

    calls = []
    try:
        # Query calls from the project
        for call in client.calls_query_stream(
            filter={
                "trace_roots_only": False,
            },
            limit=500,
        ):
            # Check if call has scores (feedback)
            call_dict = {
                "id": call.id,
                "op_name": call.op_name,
                "started_at": call.started_at,
                "output": call.output,
            }

            # Try to get feedback/scores
            try:
                if hasattr(call, 'feedback') and call.feedback:
                    call_dict["feedback"] = list(call.feedback)
                if hasattr(call, 'summary') and call.summary:
                    call_dict["summary"] = call.summary
            except Exception:
                pass

            calls.append(call_dict)

    except Exception as e:
        logger.error(f"Failed to query Weave calls: {e}")

    logger.info(f"Retrieved {len(calls)} calls from Weave")
    return calls


def extract_scores_from_call(call: dict[str, Any]) -> dict[str, float]:
    """Extract scores from a call's feedback/summary."""
    scores = {}

    # Check summary for scores (apply_scorer results go here)
    summary = call.get("summary", {})
    if isinstance(summary, dict):
        weave_summary = summary.get("weave", {})
        if isinstance(weave_summary, dict):
            # Scores from apply_scorer appear under the scorer name
            for key, value in weave_summary.items():
                if isinstance(value, dict):
                    # AttackEffectivenessScorer results
                    if "effectiveness" in value:
                        scores["effectiveness"] = float(value["effectiveness"])
                    # GraderAccuracyScorer results
                    if "accuracy_score" in value:
                        scores["accuracy"] = float(value["accuracy_score"])
                    if "reasoning_quality" in value:
                        scores["reasoning_quality"] = float(value["reasoning_quality"])

    # Also check feedback
    feedback = call.get("feedback", [])
    for fb in feedback:
        if isinstance(fb, dict):
            if fb.get("feedback_type") == "score":
                payload = fb.get("payload", {})
                if "score" in payload:
                    scores["feedback_score"] = float(payload["score"])

    return scores


def update_registry_from_scores(
    calls: list[dict[str, Any]],
    dry_run: bool = False,
) -> dict[str, int]:
    """Update prompt registry with scores from calls."""
    from ai_health_board.improvement import get_registry

    registry = get_registry()
    stats = {"processed": 0, "updated": 0, "skipped": 0}

    for call in calls:
        op_name = call.get("op_name", "")

        # Find matching prompt ID
        prompt_id = None
        for op_pattern, pid in OP_TO_PROMPT_MAP.items():
            if op_pattern in op_name:
                prompt_id = pid
                break

        if not prompt_id:
            stats["skipped"] += 1
            continue

        # Extract scores
        scores = extract_scores_from_call(call)
        if not scores:
            stats["skipped"] += 1
            continue

        stats["processed"] += 1

        # Determine success and score
        # For tester: effectiveness > 0.5 is success
        # For grader: accuracy > 0.7 is success
        if "effectiveness" in scores:
            success = scores["effectiveness"] > 0.5
            score = scores["effectiveness"]
        elif "accuracy" in scores:
            success = scores["accuracy"] > 0.7
            score = scores["accuracy"]
        elif "feedback_score" in scores:
            success = scores["feedback_score"] > 0.5
            score = scores["feedback_score"]
        else:
            continue

        if dry_run:
            logger.info(f"[DRY RUN] Would update {prompt_id}: success={success}, score={score:.2f}")
        else:
            registry.record_usage(prompt_id, success=success, score=score)
            stats["updated"] += 1
            logger.debug(f"Updated {prompt_id}: success={success}, score={score:.2f}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Sync Weave scores to prompt registry")
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Hours of history to query (default: 24)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes",
    )
    args = parser.parse_args()

    logger.info(f"Syncing Weave scores from last {args.hours} hours")

    # Query recent calls
    calls = query_recent_calls(hours=args.hours)

    if not calls:
        logger.info("No calls found to process")
        return 0

    # Update registry
    stats = update_registry_from_scores(calls, dry_run=args.dry_run)

    print(f"\n=== Sync Complete ===")
    print(f"Calls processed: {stats['processed']}")
    print(f"Registry updated: {stats['updated']}")
    print(f"Skipped (no scores/no mapping): {stats['skipped']}")

    if args.dry_run:
        print("\n[DRY RUN] No changes made. Run without --dry-run to apply.")

    # Show updated registry stats
    if not args.dry_run and stats['updated'] > 0:
        from ai_health_board.improvement import get_registry
        registry = get_registry()

        print(f"\n=== Updated Prompt Stats ===")
        for prompt_id in sorted(OP_TO_PROMPT_MAP.values()):
            stats = registry.get_performance_stats(prompt_id)
            if stats.get("usage_count", 0) > 0:
                print(f"  {prompt_id}: {stats['usage_count']} uses, {stats['success_rate']:.0%} success")

    return 0


if __name__ == "__main__":
    sys.exit(main())
