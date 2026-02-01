#!/usr/bin/env python3
"""Benchmark Tavily across multiple sources to find what works where."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# Test sources by category
TEST_SOURCES = {
    "general": {
        "name": "CDC",
        "base_url": "https://www.cdc.gov/clinical-guidance",
        "search_query": "CDC clinical guidelines treatment recommendations",
    },
    "specialty_cardiology": {
        "name": "AHA (Cardiology)",
        "base_url": "https://professional.heart.org/en/guidelines-and-statements",
        "search_query": "American Heart Association AHA clinical guidelines 2024",
    },
    "specialty_diabetes": {
        "name": "ADA (Diabetes)",
        "base_url": "https://diabetes.org/health-wellness",
        "search_query": "American Diabetes Association standards of care guidelines",
    },
    "region_ca": {
        "name": "CA Medical Board",
        "base_url": "https://www.mbc.ca.gov",
        "search_query": "California medical board telehealth prescribing regulations",
    },
}


@dataclass
class SourceResult:
    source_name: str
    category: str
    crawl_urls: int
    crawl_content_kb: float
    crawl_error: str | None
    search_urls: int
    search_content_kb: float
    search_error: str | None
    map_urls: int
    map_error: str | None
    extract_content_kb: float
    extract_error: str | None
    sample_search_titles: list[str] = field(default_factory=list)


def test_source(category: str, config: dict) -> SourceResult:
    """Test all approaches on a single source."""
    name = config["name"]
    base_url = config["base_url"]
    query = config["search_query"]

    print(f"\n{'='*60}")
    print(f"Testing: {name} ({category})")
    print(f"Base URL: {base_url}")
    print(f"Query: {query}")
    print('='*60)

    result = SourceResult(
        source_name=name,
        category=category,
        crawl_urls=0,
        crawl_content_kb=0,
        crawl_error=None,
        search_urls=0,
        search_content_kb=0,
        search_error=None,
        map_urls=0,
        map_error=None,
        extract_content_kb=0,
        extract_error=None,
    )

    # Test 1: Crawl
    print("\n  [CRAWL]...", end=" ")
    try:
        crawl_result = client.crawl(
            url=base_url,
            max_depth=2,
            limit=10,
            instructions="Find clinical guidelines and treatment recommendations",
        )
        pages = crawl_result.get("results", [])
        result.crawl_urls = len(pages)
        result.crawl_content_kb = sum(len(p.get("raw_content", "")) for p in pages) / 1024
        print(f"{result.crawl_urls} pages, {result.crawl_content_kb:.1f}KB")
    except Exception as e:
        result.crawl_error = str(e)[:100]
        print(f"ERROR: {result.crawl_error}")

    # Test 2: Search
    print("  [SEARCH]...", end=" ")
    try:
        search_result = client.search(
            query=query,
            search_depth="advanced",
            max_results=10,
            include_raw_content=True,
        )
        results = search_result.get("results", [])
        result.search_urls = len(results)
        result.search_content_kb = sum(
            len(r.get("raw_content", "") or r.get("content", ""))
            for r in results
        ) / 1024
        result.sample_search_titles = [r.get("title", "")[:60] for r in results[:3]]
        print(f"{result.search_urls} results, {result.search_content_kb:.1f}KB")
    except Exception as e:
        result.search_error = str(e)[:100]
        print(f"ERROR: {result.search_error}")

    # Test 3: Map
    print("  [MAP]...", end=" ")
    try:
        map_result = client.map(
            url=base_url,
            max_depth=2,
            limit=50,
        )
        urls = map_result.get("urls", [])
        result.map_urls = len(urls)
        print(f"{result.map_urls} URLs discovered")

        # If map found URLs, try extracting a few
        if urls:
            print("  [EXTRACT]...", end=" ")
            try:
                extract_result = client.extract(urls=urls[:5])
                pages = extract_result.get("results", [])
                result.extract_content_kb = sum(len(p.get("raw_content", "")) for p in pages) / 1024
                print(f"{len(pages)} pages, {result.extract_content_kb:.1f}KB")
            except Exception as e:
                result.extract_error = str(e)[:100]
                print(f"ERROR: {result.extract_error}")
    except Exception as e:
        result.map_error = str(e)[:100]
        print(f"ERROR: {result.map_error}")

    return result


def main():
    print("=" * 70)
    print("MULTI-SOURCE TAVILY BENCHMARK")
    print("Testing which approach works best for each source type")
    print("=" * 70)

    results = []
    for category, config in TEST_SOURCES.items():
        result = test_source(category, config)
        results.append(result)

    # Summary table
    print("\n\n" + "=" * 100)
    print("SUMMARY: What works for each source?")
    print("=" * 100)
    print(f"\n{'Source':<25} {'Crawl':<15} {'Search':<15} {'Map':<15} {'Map+Extract':<15}")
    print("-" * 100)

    for r in results:
        crawl_status = f"{r.crawl_urls}pg/{r.crawl_content_kb:.0f}KB" if r.crawl_urls > 0 else ("ERR" if r.crawl_error else "0")
        search_status = f"{r.search_urls}pg/{r.search_content_kb:.0f}KB" if r.search_urls > 0 else ("ERR" if r.search_error else "0")
        map_status = f"{r.map_urls} URLs" if r.map_urls > 0 else ("ERR" if r.map_error else "0")
        extract_status = f"{r.extract_content_kb:.0f}KB" if r.extract_content_kb > 0 else ("ERR" if r.extract_error else "-")

        print(f"{r.source_name:<25} {crawl_status:<15} {search_status:<15} {map_status:<15} {extract_status:<15}")

    print("\n" + "-" * 100)
    print("RECOMMENDATION PER CATEGORY:")
    print("-" * 100)

    for r in results:
        best = "UNKNOWN"
        if r.search_content_kb > r.crawl_content_kb and r.search_content_kb > 0:
            best = "SEARCH"
        elif r.crawl_content_kb > 0:
            best = "CRAWL"
        elif r.map_urls > 0 and r.extract_content_kb > 0:
            best = "MAP+EXTRACT"
        elif r.search_urls > 0:
            best = "SEARCH (limited)"

        print(f"  {r.category:<25} → {best}")
        if r.sample_search_titles:
            print(f"    Sample: {r.sample_search_titles[0]}")

    # Save results
    output = {
        "results": [
            {
                "source_name": r.source_name,
                "category": r.category,
                "crawl_urls": r.crawl_urls,
                "crawl_content_kb": r.crawl_content_kb,
                "crawl_error": r.crawl_error,
                "search_urls": r.search_urls,
                "search_content_kb": r.search_content_kb,
                "search_error": r.search_error,
                "map_urls": r.map_urls,
                "map_error": r.map_error,
                "extract_content_kb": r.extract_content_kb,
                "extract_error": r.extract_error,
                "sample_search_titles": r.sample_search_titles,
            }
            for r in results
        ]
    }

    with open("data/tavily_multi_benchmark.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to data/tavily_multi_benchmark.json")


if __name__ == "__main__":
    main()
