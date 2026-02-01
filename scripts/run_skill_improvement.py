#!/usr/bin/env python
"""Run the skill improvement cycle.

This uses Claude to:
1. Analyze failure patterns
2. Detect skill gaps
3. Design new skills
4. Validate and register them

Usage:
    python scripts/run_skill_improvement.py --agent-type tester [--auto-activate]

Cron example (weekly):
    0 3 * * 0 cd /path/to/project && .venv/bin/python scripts/run_skill_improvement.py --agent-type tester
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime

from loguru import logger


def get_recent_failures(agent_type: str, limit: int = 20) -> list[str]:
    """Get recent failure patterns from Weave/Redis."""
    failures = []

    # Try to get failures from attack memory
    if agent_type == "tester":
        try:
            from ai_health_board import redis_store
            # Get low-success attacks as failure patterns
            client = redis_store._get_client()
            for key in client.scan_iter(match="attack:*"):
                data = redis_store._get_json(key.decode() if isinstance(key, bytes) else key)
                if data and data.get("success_rate", 1.0) < 0.3:
                    category = data.get("category", "unknown")
                    failures.append(f"Low success rate in {category} attacks")
        except Exception as e:
            logger.warning(f"Could not load attack failures: {e}")

    # Add some common failure patterns for demonstration
    if not failures:
        if agent_type == "tester":
            failures = [
                "Target detects adversarial intent and deflects",
                "Unable to escalate symptoms naturally",
                "Boundary violations too obvious",
                "Responses don't sound like real patients",
            ]
        else:
            failures = [
                "Missing subtle safety violations",
                "Inconsistent severity ratings",
                "Not detecting scope creep",
                "False positives on emergency detection",
            ]

    return failures[:limit]


def get_current_skills(agent_type: str) -> list[str]:
    """Get list of current skills for an agent type."""
    if agent_type == "tester":
        return [
            "plan_attack",
            "next_message",
            "generate_attack",
            "record_vector_outcome",
        ]
    else:
        return [
            "scenario_context",
            "turn_analysis",
            "rubric_evaluation",
            "safety_audit",
            "quality_assessment",
            "compliance_audit",
            "severity_determination",
        ]


def main():
    parser = argparse.ArgumentParser(description="Run skill improvement cycle")
    parser.add_argument(
        "--agent-type",
        choices=["tester", "grader"],
        required=True,
        help="Agent type to improve",
    )
    parser.add_argument(
        "--auto-activate",
        action="store_true",
        help="Automatically activate validated skills",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only detect gaps, don't design skills",
    )
    args = parser.parse_args()

    logger.info(f"Starting skill improvement for {args.agent_type} at {datetime.now().isoformat()}")

    # Get failure patterns
    failures = get_recent_failures(args.agent_type)
    logger.info(f"Found {len(failures)} failure patterns")

    for f in failures:
        print(f"  - {f}")

    # Get current skills
    current_skills = get_current_skills(args.agent_type)
    logger.info(f"Current skills: {len(current_skills)}")

    if args.dry_run:
        # Just detect gaps
        from ai_health_board.improvement import detect_skill_gaps

        print("\n=== Detecting Skill Gaps ===\n")
        gaps = detect_skill_gaps(args.agent_type, failures, current_skills)

        if gaps:
            for gap in gaps:
                print(f"Gap: {gap.get('name')}")
                print(f"  Description: {gap.get('description')}")
                print(f"  Priority: {gap.get('priority')}")
                print(f"  Addresses: {gap.get('addresses_failures')}")
                print()
        else:
            print("No skill gaps detected")

        print("[DRY RUN] Run without --dry-run to design and register skills")
        return 0

    # Run full improvement cycle
    from ai_health_board.improvement import run_skill_improvement_cycle

    print("\n=== Running Skill Improvement Cycle ===\n")
    result = run_skill_improvement_cycle(
        agent_type=args.agent_type,
        failure_patterns=failures,
        current_skills=current_skills,
        auto_activate=args.auto_activate,
    )

    print(f"\n=== Results ===")
    print(f"Gaps detected: {result['gaps_detected']}")
    print(f"Skills designed: {result['skills_designed']}")
    print(f"Skills validated: {result['skills_validated']}")
    print(f"Skills registered: {result['skills_registered']}")
    print(f"Skills activated: {result['skills_activated']}")

    if result["new_skills"]:
        print(f"\nNew skills:")
        for skill in result["new_skills"]:
            print(f"  - {skill['skill_id']}: {skill['description']}")

    if result["errors"]:
        print(f"\nErrors:")
        for error in result["errors"]:
            print(f"  - {error}")

    # Show all registered skills
    from ai_health_board.improvement import get_skill_registry

    registry = get_skill_registry()
    all_skills = registry.list_skills(agent_type=args.agent_type, active_only=False)

    if all_skills:
        print(f"\n=== All Registered Skills ({args.agent_type}) ===")
        for skill in all_skills:
            status = "ACTIVE" if skill.is_active else "inactive"
            print(f"  [{status}] {skill.skill_id}")
            print(f"           {skill.description}")
            if skill.usage_count > 0:
                print(f"           Usage: {skill.usage_count}, Success: {skill.success_rate():.0%}")

    logger.info(f"Skill improvement complete at {datetime.now().isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
