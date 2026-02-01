#!/usr/bin/env python3
"""Compare broad vs targeted search strategies."""

from __future__ import annotations

import json
import os
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def test_broad_search():
    """Single broad query."""
    print("\n[BROAD SEARCH] Single comprehensive query...")

    result = client.search(
        query="clinical guidelines healthcare treatment recommendations emergency protocols",
        search_depth="advanced",
        max_results=10,
        include_raw_content=True,
    )

    results = result.get("results", [])
    total_kb = sum(len(r.get("raw_content", "")) for r in results) / 1024
    domains = set(r.get("url", "").split("/")[2] for r in results if r.get("url"))

    print(f"  Results: {len(results)}")
    print(f"  Content: {total_kb:.1f}KB")
    print(f"  Unique domains: {len(domains)}")
    print(f"  Domains: {list(domains)[:5]}")

    return {
        "strategy": "broad",
        "queries": 1,
        "results": len(results),
        "content_kb": total_kb,
        "unique_domains": len(domains),
    }


def test_targeted_searches():
    """Multiple targeted queries."""
    print("\n[TARGETED SEARCH] Multiple specific queries...")

    queries = [
        "CDC emergency clinical guidelines",
        "heart failure treatment guidelines 2024",
        "California telehealth prescribing regulations",
        "nurse practitioner scope of practice",
    ]

    all_results = []
    all_urls = set()

    for q in queries:
        result = client.search(
            query=q,
            search_depth="basic",  # Basic since we're doing multiple
            max_results=5,
            include_raw_content=True,
        )
        results = result.get("results", [])
        for r in results:
            url = r.get("url", "")
            if url not in all_urls:
                all_urls.add(url)
                all_results.append(r)

    total_kb = sum(len(r.get("raw_content") or "") for r in all_results) / 1024
    domains = set(r.get("url", "").split("/")[2] for r in all_results if r.get("url"))

    print(f"  Queries: {len(queries)}")
    print(f"  Unique results: {len(all_results)}")
    print(f"  Content: {total_kb:.1f}KB")
    print(f"  Unique domains: {len(domains)}")
    print(f"  Domains: {list(domains)[:5]}")

    return {
        "strategy": "targeted",
        "queries": len(queries),
        "results": len(all_results),
        "content_kb": total_kb,
        "unique_domains": len(domains),
    }


def test_domain_focused():
    """Domain-constrained searches."""
    print("\n[DOMAIN-FOCUSED] Queries constrained to specific domains...")

    domain_queries = [
        ("cdc.gov", "clinical guidelines emergency protocols"),
        ("heart.org", "heart failure guidelines"),
        ("ca.gov", "medical board telehealth"),
    ]

    all_results = []

    for domain, query in domain_queries:
        result = client.search(
            query=query,
            search_depth="advanced",
            max_results=5,
            include_raw_content=True,
            include_domains=[domain],
        )
        results = result.get("results", [])
        all_results.extend(results)
        print(f"  {domain}: {len(results)} results")

    total_kb = sum(len(r.get("raw_content") or "") for r in all_results) / 1024

    print(f"  Total results: {len(all_results)}")
    print(f"  Content: {total_kb:.1f}KB")

    return {
        "strategy": "domain-focused",
        "queries": len(domain_queries),
        "results": len(all_results),
        "content_kb": total_kb,
        "unique_domains": len(domain_queries),
    }


def main():
    print("=" * 70)
    print("SEARCH STRATEGY COMPARISON")
    print("=" * 70)

    results = []
    results.append(test_broad_search())
    results.append(test_targeted_searches())
    results.append(test_domain_focused())

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\n{'Strategy':<18} {'Queries':<10} {'Results':<10} {'Content KB':<12} {'Domains':<10}")
    print("-" * 70)

    for r in results:
        print(f"{r['strategy']:<18} {r['queries']:<10} {r['results']:<10} {r['content_kb']:<12.1f} {r['unique_domains']:<10}")

    # Recommend
    print("\n" + "-" * 70)
    best = max(results, key=lambda x: x["content_kb"])
    print(f"WINNER: {best['strategy'].upper()} ({best['content_kb']:.1f}KB from {best['results']} results)")

    with open("data/tavily_strategy_comparison.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
