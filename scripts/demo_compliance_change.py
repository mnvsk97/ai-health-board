#!/usr/bin/env python3
"""
Compliance Change Demo Script: Demonstrate the compliance monitoring workflow.

This script demonstrates:
1. List current guidelines registered in the system
2. Simulate a guideline change (version/hash update)
3. Show new scenario generated from the updated guideline
4. Display compliance status becoming "outdated"

Usage:
    python scripts/demo_compliance_change.py
    python scripts/demo_compliance_change.py --guideline-id cdc-covid-guidelines
    python scripts/demo_compliance_change.py --create-demo-guideline
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import time

# Add project root to path
sys.path.insert(0, str(__file__).rsplit("/scripts", 1)[0])

from ai_health_board import redis_store
from ai_health_board.compliance import register_guideline, simulate_guideline_change
from ai_health_board.models import Guideline


def create_demo_guideline() -> Guideline:
    """Create a demo guideline for testing."""
    guideline = Guideline(
        guideline_id="demo-cdc-covid-isolation",
        source_url="https://www.cdc.gov/respiratory-viruses/guidance/respiratory-virus-guidance.html",
        state="CA",
        specialty="primary_care",
        version="2024-01-15",
        hash=hashlib.sha256(b"initial_content").hexdigest(),
        last_checked=time.time(),
    )
    register_guideline(guideline)
    print(f"Created demo guideline: {guideline.guideline_id}")
    return guideline


def list_guidelines() -> list[Guideline]:
    """List all registered guidelines."""
    guidelines = redis_store.list_guidelines()

    print("\n" + "=" * 60)
    print("REGISTERED GUIDELINES")
    print("=" * 60)

    if not guidelines:
        print("  No guidelines registered.")
        print("\n  Use --create-demo-guideline to create a test guideline")
        print("  Or run: python scripts/discover_guidelines.py --url <url>")
        return []

    for g in guidelines:
        last_checked = time.strftime("%Y-%m-%d %H:%M", time.localtime(g.last_checked))
        print(f"\n  ID:           {g.guideline_id}")
        print(f"  Source:       {g.source_url[:50]}{'...' if len(g.source_url) > 50 else ''}")
        print(f"  Version:      {g.version}")
        print(f"  State:        {g.state or 'N/A'}")
        print(f"  Specialty:    {g.specialty or 'N/A'}")
        print(f"  Hash:         {g.hash[:16]}...")
        print(f"  Last Checked: {last_checked}")

    print(f"\nTotal: {len(guidelines)} guideline(s)")
    return guidelines


def check_compliance_status(target_id: str) -> None:
    """Check and display compliance status for a target."""
    status = redis_store.get_compliance_status(target_id)

    print("\n" + "-" * 60)
    print("COMPLIANCE STATUS")
    print("-" * 60)

    if not status:
        print(f"  Target ID:    {target_id}")
        print(f"  Status:       UNKNOWN (no status recorded)")
        return

    updated = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(status.updated_at))
    status_display = status.status.upper()

    # Add visual indicator
    if status.status == "valid":
        indicator = "[OK]"
    elif status.status == "outdated":
        indicator = "[!!]"
    else:
        indicator = "[..]"

    print(f"  Target ID:    {target_id}")
    print(f"  Status:       {indicator} {status_display}")
    print(f"  Reason:       {status.reason or 'N/A'}")
    print(f"  Updated At:   {updated}")

    if status.status == "outdated":
        print("\n  ⚠️  COMPLIANCE OUTDATED - Re-testing required!")
        print("      Run: python scripts/run_e2e_demo.py to re-test")


def simulate_change(guideline_id: str, target_id: str) -> None:
    """Simulate a guideline change and show results."""
    print("\n" + "=" * 60)
    print("SIMULATING GUIDELINE CHANGE")
    print("=" * 60)

    # Get current guideline state
    guideline = redis_store.get_guideline(guideline_id)
    if not guideline:
        print(f"\n  ERROR: Guideline '{guideline_id}' not found")
        print("  Available guidelines:")
        for g in redis_store.list_guidelines():
            print(f"    - {g.guideline_id}")
        return

    print(f"\n  Guideline: {guideline_id}")
    print(f"  Current Version: {guideline.version}")
    print(f"  Current Hash: {guideline.hash[:16]}...")

    print("\n  Simulating change...")

    # Simulate the change
    new_scenario = simulate_guideline_change(guideline_id, target_id)

    # Get updated guideline
    updated_guideline = redis_store.get_guideline(guideline_id)

    print(f"\n  New Version: {updated_guideline.version}")
    print(f"  New Hash: {updated_guideline.hash[:16]}...")

    # Show the new scenario
    if new_scenario:
        print("\n" + "-" * 60)
        print("NEW SCENARIO GENERATED")
        print("-" * 60)
        print(f"  ID:          {new_scenario.scenario_id}")
        print(f"  Title:       {new_scenario.title}")
        print(f"  Source Type: {new_scenario.source_type}")
        print(f"  State:       {new_scenario.state or 'N/A'}")
        print(f"  Specialty:   {new_scenario.specialty or 'N/A'}")
        print(f"\n  Description:")
        # Wrap description
        desc = new_scenario.description
        for line in desc.split("\n")[:5]:
            print(f"    {line[:70]}{'...' if len(line) > 70 else ''}")
        if len(desc.split("\n")) > 5:
            print(f"    ... ({len(desc.split(chr(10)))} lines total)")

        print(f"\n  Rubric Criteria: {len(new_scenario.rubric_criteria)} items")
        for i, criterion in enumerate(new_scenario.rubric_criteria[:5], 1):
            print(f"    {i}. {criterion.criterion[:60]}{'...' if len(criterion.criterion) > 60 else ''}")
            print(f"       Points: {criterion.points}, Tags: {criterion.tags}")
        if len(new_scenario.rubric_criteria) > 5:
            print(f"    ... and {len(new_scenario.rubric_criteria) - 5} more")
    else:
        print("\n  WARNING: No scenario generated")

    # Show compliance status
    check_compliance_status(target_id)


def main():
    parser = argparse.ArgumentParser(
        description="Demonstrate the compliance change workflow"
    )
    parser.add_argument(
        "--guideline-id",
        type=str,
        help="Specific guideline ID to simulate change on",
    )
    parser.add_argument(
        "--target-id",
        type=str,
        default="intake-agent-prod",
        help="Target ID for compliance tracking (default: intake-agent-prod)",
    )
    parser.add_argument(
        "--create-demo-guideline",
        action="store_true",
        help="Create a demo guideline before simulation",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Only list guidelines without simulating changes",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("COMPLIANCE CHANGE DEMO")
    print("=" * 60)
    print(f"Target ID: {args.target_id}")

    # Create demo guideline if requested
    if args.create_demo_guideline:
        create_demo_guideline()

    # List current guidelines
    guidelines = list_guidelines()

    if args.list_only:
        check_compliance_status(args.target_id)
        return

    if not guidelines:
        print("\nNo guidelines available to simulate changes.")
        print("Options:")
        print("  1. Create a demo guideline: --create-demo-guideline")
        print("  2. Discover real guidelines: python scripts/discover_guidelines.py")
        sys.exit(1)

    # Determine which guideline to update
    guideline_id = args.guideline_id
    if not guideline_id:
        # Use the first available guideline
        guideline_id = guidelines[0].guideline_id
        print(f"\nNo guideline specified, using: {guideline_id}")

    # Simulate the change
    simulate_change(guideline_id, args.target_id)

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. View frontend notification: cd frontend && npm run dev")
    print("  2. Re-run tests: python scripts/run_e2e_demo.py")
    print("  3. Check API: curl http://localhost:8000/compliance/status/intake-agent-prod")


if __name__ == "__main__":
    main()
