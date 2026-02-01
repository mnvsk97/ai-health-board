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

    # Recursively crawl links (same-domain) and extract guidelines
    uv run python scripts/discover_guidelines.py --url "..." --recursive --max-pages 25 --max-depth 2
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import deque
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

# Add project root to path for script execution
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx  # noqa: E402

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


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for name, value in attrs:
            if name.lower() == "href" and value:
                self.links.append(value)


def _extract_links(html: str, base_url: str) -> list[str]:
    parser = _LinkParser()
    parser.feed(html)
    resolved: list[str] = []
    for href in parser.links:
        if href.startswith("javascript:") or href.startswith("mailto:"):
            continue
        absolute = urljoin(base_url, href)
        resolved.append(absolute)
    return resolved


def _same_domain(url: str, root: str) -> bool:
    return urlparse(url).netloc == urlparse(root).netloc


def _default_include_patterns(start_url: str) -> list[str]:
    if "/guidelines" in urlparse(start_url).path:
        return ["/guidelines"]
    return []


def _default_exclude_patterns() -> list[str]:
    return [
        "/home",
        "/store",
        "/login",
        "/donate",
        "/news",
        "/events",
        "/press",
        "/about",
        "/contact",
        "/jobs",
        "/careers",
    ]


def _matches_patterns(url: str, patterns: list[str]) -> bool:
    return any(p in url for p in patterns)


def _crawl_links(
    start_url: str,
    max_pages: int,
    max_depth: int,
    same_domain_only: bool,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> list[str]:
    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(start_url, 0)])
    discovered: list[str] = []

    include_patterns = include_patterns or _default_include_patterns(start_url)
    exclude_patterns = exclude_patterns or _default_exclude_patterns()

    client = httpx.Client(timeout=20, follow_redirects=True)
    try:
        while queue and len(visited) < max_pages:
            url, depth = queue.popleft()
            if url in visited or depth > max_depth:
                continue
            if same_domain_only and not _same_domain(url, start_url):
                continue
            if exclude_patterns and _matches_patterns(url, exclude_patterns):
                continue
            if include_patterns and not _matches_patterns(url, include_patterns):
                continue
            visited.add(url)
            discovered.append(url)

            try:
                resp = client.get(url)
                resp.raise_for_status()
            except Exception as exc:
                print(f"Failed to fetch {url}: {exc}")
                continue

            if depth == max_depth:
                continue

            links = _extract_links(resp.text, url)
            for link in links:
                if link not in visited and len(visited) + len(queue) < max_pages:
                    queue.append((link, depth + 1))
    finally:
        client.close()

    return discovered


def _extract_links_from_stagehand(result: object) -> list[str]:
    candidates: list[object] = []
    if hasattr(result, "data") and result.data:
        candidates = list(result.data) if hasattr(result.data, "__iter__") else []
    elif hasattr(result, "model_dump"):
        data = result.model_dump()
        if isinstance(data, list):
            candidates = data
    elif isinstance(result, dict):
        if "result" in result and isinstance(result["result"], list):
            candidates = result["result"]
    elif isinstance(result, list):
        candidates = result

    flattened: list[str] = []
    for item in candidates:
        if isinstance(item, str):
            flattened.append(item)
        elif isinstance(item, list):
            for sub in item:
                if isinstance(sub, str):
                    flattened.append(sub)
    return flattened


def _crawl_links_browser(
    start_url: str,
    max_pages: int,
    max_depth: int,
    same_domain_only: bool,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> list[str]:
    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(start_url, 0)])
    discovered: list[str] = []

    include_patterns = include_patterns or _default_include_patterns(start_url)
    exclude_patterns = exclude_patterns or _default_exclude_patterns()

    with StagehandClient() as client:
        while queue and len(visited) < max_pages:
            url, depth = queue.popleft()
            if url in visited or depth > max_depth:
                continue
            if same_domain_only and not _same_domain(url, start_url):
                continue
            if exclude_patterns and _matches_patterns(url, exclude_patterns):
                continue
            if include_patterns and not _matches_patterns(url, include_patterns):
                continue
            visited.add(url)
            discovered.append(url)

            if depth == max_depth:
                continue

            print(f"Discovering links via Stagehand: {url}")
            client.navigate(url)
            client.observe("Identify all outbound links and guideline-related URLs on the page.")
            result = client.extract(
                instruction=(
                    "Extract every unique URL (href) visible on this page. "
                    "Return only valid http/https URLs."
                ),
                schema={"type": "array", "items": {"type": "string", "format": "uri"}},
            )
            links = _extract_links_from_stagehand(result)
            for link in links:
                if link not in visited and len(visited) + len(queue) < max_pages:
                    queue.append((link, depth + 1))

    return discovered

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
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively crawl links starting from --url",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=10,
        help="Maximum number of pages to crawl when --recursive is set",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=1,
        help="Maximum crawl depth when --recursive is set",
    )
    parser.add_argument(
        "--allow-cross-domain",
        action="store_true",
        help="Allow crawling links outside the start URL's domain",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=None,
        help="Substring pattern to include when crawling (can be repeated)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=None,
        help="Substring pattern to exclude when crawling (can be repeated)",
    )
    args = parser.parse_args()

    try:
        urls = [args.url]
        if args.recursive:
            crawler = _crawl_links_browser if args.browser else _crawl_links
            urls = crawler(
                args.url,
                max_pages=args.max_pages,
                max_depth=args.max_depth,
                same_domain_only=not args.allow_cross_domain,
                include_patterns=args.include,
                exclude_patterns=args.exclude,
            )
            print(f"Discovered {len(urls)} page(s) to extract")

        for url in urls:
            if args.browser:
                extract_with_browser(url, dry_run=args.dry_run)
            else:
                extract_with_http(url, dry_run=args.dry_run)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
