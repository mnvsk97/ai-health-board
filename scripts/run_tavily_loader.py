#!/usr/bin/env python3
"""Load guidelines using Tavily + Browserbase and feed into the ADK pipeline."""

from __future__ import annotations

import argparse
import asyncio

from ai_health_board import redis_store
from ai_health_board.tavily_loader import TavilyGuidelineLoader


def main():
    parser = argparse.ArgumentParser(
        description="Load clinical guidelines via Tavily + Browserbase hybrid pipeline"
    )
    parser.add_argument(
        "--category",
        choices=["general", "specialty", "region", "role", "all"],
        default="all",
        help="Category to load",
    )
    parser.add_argument(
        "--subcategory",
        help="Subcategory (e.g., cardiology, CA, nurse)",
    )
    parser.add_argument(
        "--max-per-source",
        type=int,
        default=5,
        help="Max guidelines per source",
    )
    parser.add_argument(
        "--no-browserbase",
        action="store_true",
        help="Disable Browserbase (faster but lower quality)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List currently stored guidelines",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all stored guidelines before loading",
    )
    parser.add_argument(
        "--run-pipeline",
        action="store_true",
        help="Run ADK scenario pipeline after loading",
    )

    args = parser.parse_args()

    if args.list:
        guidelines = redis_store.list_extracted_guidelines()
        print(f"\nStored guidelines: {len(guidelines)}")

        # Group by category
        by_category = {}
        for g in guidelines:
            cat = g.get("category", "unknown")
            by_category.setdefault(cat, []).append(g)

        for cat, items in sorted(by_category.items()):
            print(f"\n  [{cat.upper()}] ({len(items)} guidelines)")
            for g in items[:5]:
                method = g.get("extraction_method", "unknown")
                print(f"    • {g.get('title', 'Untitled')[:55]} ({method})")
            if len(items) > 5:
                print(f"    ... and {len(items) - 5} more")
        return

    if args.clear:
        print("Clearing stored guidelines...")
        # Clear guidelines from Redis
        guidelines = redis_store.list_extracted_guidelines()
        for g in guidelines:
            url = g.get("source_url", "")
            if url:
                key = f"guideline:extracted:{redis_store._url_to_key(url)}"
                redis_store._redis_client().delete(key)
        print(f"Cleared {len(guidelines)} guidelines")

    # Load guidelines
    print("=" * 70)
    print("TAVILY + BROWSERBASE GUIDELINE LOADER")
    print("=" * 70)
    print(f"Browserbase: {'DISABLED' if args.no_browserbase else 'ENABLED (high quality)'}")
    print("=" * 70)

    loader = TavilyGuidelineLoader(use_browserbase=not args.no_browserbase)

    if args.category == "all":
        counts = loader.load_all(max_per_source=args.max_per_source)
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        for cat, count in counts.items():
            print(f"  {cat}: {count} guidelines")
        total = sum(counts.values())
        print(f"\n  TOTAL: {total} guidelines loaded")
    else:
        guidelines = loader.load_category(
            category=args.category,
            subcategory=args.subcategory,
            max_per_source=args.max_per_source,
        )
        print(f"\nLoaded {len(guidelines)} guidelines")
        for g in guidelines[:10]:
            method = g.get("extraction_method", "unknown")
            print(f"  • {g.get('title', 'Untitled')[:55]} ({method})")

    # Optionally run the ADK pipeline
    if args.run_pipeline:
        print("\n" + "=" * 60)
        print("RUNNING ADK SCENARIO PIPELINE")
        print("=" * 60)

        from google.adk.runners import InMemoryRunner
        from google.adk.sessions import Session
        from ai_health_board.agents.scenario_agent import build_scenario_workflow_agent

        agent = build_scenario_workflow_agent()
        runner = InMemoryRunner(agent=agent, app_name="scenario_pipeline")

        session = Session(app_name="scenario_pipeline")
        session.state["run_id"] = "tavily_load_run"
        session.state["bench_limit"] = 0  # Skip HealthBench, only use web guidelines

        async def run():
            async for event in runner.run_async(session=session):
                if event.actions and event.actions.state_delta:
                    for key, value in event.actions.state_delta.items():
                        if key == "published_scenario_ids":
                            print(f"\nPublished scenarios: {len(value)}")
                            for sid in value[:5]:
                                print(f"  - {sid}")

        asyncio.run(run())


if __name__ == "__main__":
    main()
