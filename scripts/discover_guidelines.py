#!/usr/bin/env python3
"""CLI script for discovering and processing clinical guidelines.

This script extracts clinical guidelines from URLs, detects new/updated content,
and automatically generates test scenarios.

Usage:
    # Test a specific URL (uses HTTP + LLM extraction)
    uv run python scripts/discover_guidelines.py --url "https://example.com/guideline"

    # Dry run (don't save to Redis)
    uv run python scripts/discover_guidelines.py --url "..." --dry-run

    # Use Stagehand browser automation instead of HTTP
    uv run python scripts/discover_guidelines.py --url "..." --browser
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Add project root to path for script execution
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ai_health_board import redis_store  # noqa: E402
from ai_health_board.browser_agent import (  # noqa: E402
    ChangeDetector,
    GuidelineExtractor,
    HTTPGuidelineExtractor,
    StagehandClient,
)
from ai_health_board.observability import init_weave, trace_op  # noqa: E402
from ai_health_board.scenario_pipeline import generate_scenario_from_guideline  # noqa: E402


def print_guideline(guideline: dict) -> None:
    """Pretty print a guideline."""
    print(f"\n{'='*60}")
    print("Extracted Guideline Data:")
    print(f"{'='*60}")
    for key, value in guideline.items():
        if isinstance(value, list):
            print(f"  {key}:")
            for item in value:
                print(f"    - {item}")
        else:
            print(f"  {key}: {value}")


@trace_op("discovery.extract_http")
def extract_with_http(url: str, dry_run: bool = False) -> dict | None:
    """Extract a guideline using HTTP + LLM.

    Args:
        url: The URL to extract from.
        dry_run: If True, don't save to Redis or generate scenarios.

    Returns:
        The extracted guideline data or None on failure.
    """
    print(f"\n{'='*60}")
    print(f"Extracting (HTTP): {url}")
    print(f"{'='*60}\n")

    with HTTPGuidelineExtractor() as extractor:
        guideline = extractor.extract_guideline(url)
        print_guideline(guideline)

        if not dry_run:
            return save_guideline_and_scenario(guideline)
        else:
            print("\n(Dry run - no changes saved)")
            return guideline

    return None


@trace_op("discovery.extract_browser")
def extract_with_browser(url: str, dry_run: bool = False) -> dict | None:
    """Extract a guideline using Stagehand browser automation.

    Args:
        url: The URL to extract from.
        dry_run: If True, don't save to Redis or generate scenarios.

    Returns:
        The extracted guideline data or None on failure.
    """
    print(f"\n{'='*60}")
    print(f"Extracting (Browser): {url}")
    print(f"{'='*60}\n")

    with StagehandClient() as client:
        extractor = GuidelineExtractor(client)
        guideline = extractor.extract_guideline(url)
        print_guideline(guideline)

        if not dry_run:
            return save_guideline_and_scenario(guideline)
        else:
            print("\n(Dry run - no changes saved)")
            return guideline

    return None


def save_guideline_and_scenario(guideline: dict) -> dict:
    """Save a guideline to Redis and generate a scenario.

    Args:
        guideline: The extracted guideline data.

    Returns:
        The guideline with added metadata.
    """
    detector = ChangeDetector()
    is_new, reason = detector.is_new_or_updated(guideline)

    print(f"\n[{reason.upper()}] {guideline.get('title', 'Unknown')}")

    # Add hash and timestamp
    guideline["hash"] = detector.compute_hash(guideline)
    guideline["extracted_at"] = time.time()

    # Save the extracted guideline
    redis_store.save_extracted_guideline(guideline)
    print("  -> Saved guideline to Redis")

    # Generate a test scenario from the guideline
    scenario = generate_scenario_from_guideline(guideline)
    redis_store.save_scenario(scenario)
    print(f"  -> Created scenario: {scenario.scenario_id}")

    # Print scenario details
    print(f"\n{'='*60}")
    print("Generated Scenario:")
    print(f"{'='*60}")
    print(f"  ID: {scenario.scenario_id}")
    print(f"  Title: {scenario.title}")
    print(f"  Description: {scenario.description}")
    print(f"  Specialty: {scenario.specialty}")
    print(f"  Rubric Criteria:")
    for criterion in scenario.rubric_criteria:
        print(f"    - {criterion.criterion} ({criterion.points} pts)")

    return guideline


def main() -> None:
    """Main entry point for the CLI."""
    init_weave()

    parser = argparse.ArgumentParser(
        description="Extract and process clinical guidelines"
    )
    parser.add_argument(
        "--url",
        type=str,
        required=True,
        help="URL of the guideline to extract",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without saving to Redis or generating scenarios",
    )
    parser.add_argument(
        "--browser",
        action="store_true",
        help="Use Stagehand browser automation instead of HTTP + LLM",
    )
    args = parser.parse_args()

    try:
        if args.browser:
            extract_with_browser(args.url, dry_run=args.dry_run)
        else:
            extract_with_http(args.url, dry_run=args.dry_run)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
