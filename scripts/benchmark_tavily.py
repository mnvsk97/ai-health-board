#!/usr/bin/env python3
"""Benchmark different Tavily approaches for guideline extraction."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# Test targets
CDC_BASE = "https://www.cdc.gov/clinical-guidance"
CDC_QUERY = "CDC clinical guidelines emergency protocols"


@dataclass
class BenchmarkResult:
    approach: str
    urls_found: int
    pages_with_content: int
    avg_content_length: int
    total_content_chars: int
    api_calls: int
    duration_seconds: float
    sample_titles: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    raw_urls: list[str] = field(default_factory=list)


def benchmark_crawl_first(url: str, limit: int = 10) -> BenchmarkResult:
    """Approach 1: Direct crawl with instructions."""
    print(f"\n[CRAWL-FIRST] Crawling {url} with limit={limit}...")
    start = time.time()
    errors = []

    try:
        result = client.crawl(
            url=url,
            max_depth=2,
            limit=limit,
            instructions="Find clinical guidelines, treatment recommendations, and emergency protocols",
            extract_depth="basic",
            format="markdown",
        )

        pages = result.get("results", [])
        urls = [p.get("url", "") for p in pages]
        contents = [p.get("raw_content", "") for p in pages]
        pages_with_content = sum(1 for c in contents if c and len(c) > 100)
        total_chars = sum(len(c) for c in contents)
        avg_len = total_chars // len(contents) if contents else 0

        # Extract titles from content (first line usually)
        titles = []
        for c in contents[:5]:
            if c:
                first_line = c.split("\n")[0].strip("# ").strip()[:80]
                if first_line:
                    titles.append(first_line)

        return BenchmarkResult(
            approach="crawl-first",
            urls_found=len(urls),
            pages_with_content=pages_with_content,
            avg_content_length=avg_len,
            total_content_chars=total_chars,
            api_calls=1,
            duration_seconds=time.time() - start,
            sample_titles=titles,
            raw_urls=urls[:10],
            errors=errors,
        )
    except Exception as e:
        errors.append(str(e))
        return BenchmarkResult(
            approach="crawl-first",
            urls_found=0,
            pages_with_content=0,
            avg_content_length=0,
            total_content_chars=0,
            api_calls=1,
            duration_seconds=time.time() - start,
            errors=errors,
        )


def benchmark_search_first(query: str, max_results: int = 10) -> BenchmarkResult:
    """Approach 2: Search then extract."""
    print(f"\n[SEARCH-FIRST] Searching '{query}' then extracting...")
    start = time.time()
    errors = []
    api_calls = 0

    try:
        # Step 1: Search
        search_result = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_raw_content=True,
        )
        api_calls += 1

        results = search_result.get("results", [])
        urls = [r.get("url", "") for r in results]

        # Content comes from search with include_raw_content
        contents = [r.get("raw_content", "") or r.get("content", "") for r in results]
        pages_with_content = sum(1 for c in contents if c and len(c) > 100)
        total_chars = sum(len(c) for c in contents)
        avg_len = total_chars // len(contents) if contents else 0

        titles = [r.get("title", "")[:80] for r in results[:5]]

        return BenchmarkResult(
            approach="search-first",
            urls_found=len(urls),
            pages_with_content=pages_with_content,
            avg_content_length=avg_len,
            total_content_chars=total_chars,
            api_calls=api_calls,
            duration_seconds=time.time() - start,
            sample_titles=titles,
            raw_urls=urls[:10],
            errors=errors,
        )
    except Exception as e:
        errors.append(str(e))
        return BenchmarkResult(
            approach="search-first",
            urls_found=0,
            pages_with_content=0,
            avg_content_length=0,
            total_content_chars=0,
            api_calls=api_calls,
            duration_seconds=time.time() - start,
            errors=errors,
        )


def benchmark_map_extract(url: str, limit: int = 20) -> BenchmarkResult:
    """Approach 3: Map structure, then extract."""
    print(f"\n[MAP-EXTRACT] Mapping {url} then extracting...")
    start = time.time()
    errors = []
    api_calls = 0

    try:
        # Step 1: Map the site
        map_result = client.map(url=url, max_depth=2, limit=limit)
        api_calls += 1

        all_urls = map_result.get("urls", [])
        print(f"  Map found {len(all_urls)} URLs")

        # Filter to likely guideline URLs
        filtered_urls = [
            u for u in all_urls
            if any(kw in u.lower() for kw in ["guidance", "guideline", "clinical", "recommendation", "treatment"])
        ]
        print(f"  Filtered to {len(filtered_urls)} guideline-like URLs")

        if not filtered_urls:
            # Fallback: take first N urls
            filtered_urls = all_urls[:10]

        # Step 2: Extract content (max 20)
        extract_urls = filtered_urls[:10]
        if extract_urls:
            extract_result = client.extract(urls=extract_urls)
            api_calls += 1

            pages = extract_result.get("results", [])
            contents = [p.get("raw_content", "") for p in pages]
            pages_with_content = sum(1 for c in contents if c and len(c) > 100)
            total_chars = sum(len(c) for c in contents)
            avg_len = total_chars // len(contents) if contents else 0

            titles = []
            for c in contents[:5]:
                if c:
                    first_line = c.split("\n")[0].strip("# ").strip()[:80]
                    if first_line:
                        titles.append(first_line)

            return BenchmarkResult(
                approach="map-extract",
                urls_found=len(all_urls),
                pages_with_content=pages_with_content,
                avg_content_length=avg_len,
                total_content_chars=total_chars,
                api_calls=api_calls,
                duration_seconds=time.time() - start,
                sample_titles=titles,
                raw_urls=extract_urls[:10],
                errors=errors,
            )
        else:
            return BenchmarkResult(
                approach="map-extract",
                urls_found=len(all_urls),
                pages_with_content=0,
                avg_content_length=0,
                total_content_chars=0,
                api_calls=api_calls,
                duration_seconds=time.time() - start,
                errors=["No guideline URLs found after filtering"],
            )
    except Exception as e:
        errors.append(str(e))
        return BenchmarkResult(
            approach="map-extract",
            urls_found=0,
            pages_with_content=0,
            avg_content_length=0,
            total_content_chars=0,
            api_calls=api_calls,
            duration_seconds=time.time() - start,
            errors=errors,
        )


def benchmark_search_crawl(query: str) -> BenchmarkResult:
    """Approach 4: Search to find base URL, then crawl."""
    print(f"\n[SEARCH-CRAWL] Searching '{query}' then crawling best result...")
    start = time.time()
    errors = []
    api_calls = 0

    try:
        # Step 1: Search to find authoritative source
        search_result = client.search(
            query=query,
            search_depth="basic",
            max_results=5,
        )
        api_calls += 1

        results = search_result.get("results", [])
        if not results:
            return BenchmarkResult(
                approach="search-crawl",
                urls_found=0,
                pages_with_content=0,
                avg_content_length=0,
                total_content_chars=0,
                api_calls=api_calls,
                duration_seconds=time.time() - start,
                errors=["No search results"],
            )

        # Get the top result's domain
        top_url = results[0].get("url", "")
        print(f"  Top search result: {top_url}")

        # Step 2: Crawl from that URL
        crawl_result = client.crawl(
            url=top_url,
            max_depth=1,
            limit=10,
            instructions="Find related clinical guidelines and recommendations",
        )
        api_calls += 1

        pages = crawl_result.get("results", [])
        urls = [p.get("url", "") for p in pages]
        contents = [p.get("raw_content", "") for p in pages]
        pages_with_content = sum(1 for c in contents if c and len(c) > 100)
        total_chars = sum(len(c) for c in contents)
        avg_len = total_chars // len(contents) if contents else 0

        titles = []
        for c in contents[:5]:
            if c:
                first_line = c.split("\n")[0].strip("# ").strip()[:80]
                if first_line:
                    titles.append(first_line)

        return BenchmarkResult(
            approach="search-crawl",
            urls_found=len(urls),
            pages_with_content=pages_with_content,
            avg_content_length=avg_len,
            total_content_chars=total_chars,
            api_calls=api_calls,
            duration_seconds=time.time() - start,
            sample_titles=titles,
            raw_urls=urls[:10],
            errors=errors,
        )
    except Exception as e:
        errors.append(str(e))
        return BenchmarkResult(
            approach="search-crawl",
            urls_found=0,
            pages_with_content=0,
            avg_content_length=0,
            total_content_chars=0,
            api_calls=api_calls,
            duration_seconds=time.time() - start,
            errors=errors,
        )


def print_results(results: list[BenchmarkResult]):
    """Print comparison table."""
    print("\n" + "=" * 80)
    print("BENCHMARK RESULTS")
    print("=" * 80)

    print(f"\n{'Approach':<15} {'URLs':<6} {'Content':<8} {'Avg Len':<10} {'Total KB':<10} {'APIs':<5} {'Time':<8}")
    print("-" * 80)

    for r in results:
        total_kb = r.total_content_chars / 1024
        print(f"{r.approach:<15} {r.urls_found:<6} {r.pages_with_content:<8} {r.avg_content_length:<10} {total_kb:<10.1f} {r.api_calls:<5} {r.duration_seconds:<8.2f}s")
        if r.errors:
            print(f"  ERRORS: {r.errors}")

    print("\n" + "-" * 80)
    print("SAMPLE TITLES FROM EACH APPROACH:")
    print("-" * 80)
    for r in results:
        print(f"\n{r.approach.upper()}:")
        for i, title in enumerate(r.sample_titles[:3], 1):
            print(f"  {i}. {title}")
        if r.raw_urls:
            print(f"  URLs: {r.raw_urls[:3]}")


def main():
    print("=" * 80)
    print("TAVILY APPROACH BENCHMARK")
    print(f"Target: {CDC_BASE}")
    print(f"Query: {CDC_QUERY}")
    print("=" * 80)

    results = []

    # Run each approach
    results.append(benchmark_crawl_first(CDC_BASE, limit=10))
    results.append(benchmark_search_first(CDC_QUERY, max_results=10))
    results.append(benchmark_map_extract(CDC_BASE, limit=20))
    results.append(benchmark_search_crawl(CDC_QUERY))

    # Print comparison
    print_results(results)

    # Save raw results
    output = {
        "target": CDC_BASE,
        "query": CDC_QUERY,
        "results": [
            {
                "approach": r.approach,
                "urls_found": r.urls_found,
                "pages_with_content": r.pages_with_content,
                "avg_content_length": r.avg_content_length,
                "total_content_chars": r.total_content_chars,
                "api_calls": r.api_calls,
                "duration_seconds": r.duration_seconds,
                "sample_titles": r.sample_titles,
                "raw_urls": r.raw_urls,
                "errors": r.errors,
            }
            for r in results
        ]
    }

    with open("data/tavily_benchmark.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nRaw results saved to data/tavily_benchmark.json")


if __name__ == "__main__":
    main()
