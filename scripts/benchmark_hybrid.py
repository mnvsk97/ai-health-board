#!/usr/bin/env python3
"""Test hybrid approach: Tavily Search → Browserbase extraction."""

from __future__ import annotations

import json
import os
import subprocess
import time
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def tavily_search_urls(query: str, max_results: int = 5) -> list[dict]:
    """Use Tavily to discover URLs."""
    print(f"\n[TAVILY SEARCH] {query}")

    result = tavily.search(
        query=query,
        search_depth="advanced",
        max_results=max_results,
        include_raw_content=True,
    )

    urls = []
    for r in result.get("results", []):
        url = r.get("url", "")
        title = r.get("title", "")
        tavily_content = r.get("raw_content") or r.get("content") or ""

        urls.append({
            "url": url,
            "title": title,
            "tavily_content_len": len(tavily_content),
            "tavily_preview": tavily_content[:500] if tavily_content else "",
        })
        print(f"  Found: {title[:60]}")
        print(f"         {url[:80]}")
        print(f"         Tavily content: {len(tavily_content):,} chars")

    return urls


def browserbase_extract(url: str) -> dict:
    """Use Stagehand via Node.js to extract from URL."""
    print(f"\n[BROWSERBASE] Extracting: {url[:60]}...")

    # Use raw extraction script
    script_path = "scripts/stagehand_raw_extract.mjs"

    try:
        result = subprocess.run(
            ["node", script_path, url],
            capture_output=True,
            text=True,
            timeout=60,
            cwd="/Users/saikrishna/dev/ai-health-board",
        )

        if result.returncode == 0:
            try:
                # Find the JSON line in stdout (skip log lines)
                lines = result.stdout.strip().split("\n")
                json_line = None
                for line in reversed(lines):
                    if line.strip().startswith("{"):
                        json_line = line
                        break

                if json_line:
                    data = json.loads(json_line)
                    content = data.get("content", "")
                    print(f"  Browserbase content: {len(content):,} chars")
                    return {
                        "success": True,
                        "content_len": len(content),
                        "content_preview": content[:500] if content else "",
                        "full_content": content,
                    }
                else:
                    print(f"  No JSON found in output")
                    return {"success": False, "error": "No JSON in output"}
            except json.JSONDecodeError as e:
                print(f"  JSON parse error: {e}")
                return {"success": False, "error": str(e)}
        else:
            print(f"  ERROR: {result.stderr[:200]}")
            return {"success": False, "error": result.stderr[:200]}

    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT")
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        print(f"  EXCEPTION: {e}")
        return {"success": False, "error": str(e)}


def compare_extraction(query: str):
    """Compare Tavily content vs Browserbase extraction."""
    print("\n" + "=" * 70)
    print(f"HYBRID TEST: {query}")
    print("=" * 70)

    # Step 1: Tavily discovers URLs
    urls = tavily_search_urls(query, max_results=3)

    # Step 2: Try Browserbase on each URL
    results = []
    for url_data in urls:
        url = url_data["url"]

        # Skip PDFs - Browserbase can't handle them, Tavily already extracted
        if url.endswith(".pdf"):
            print(f"\n[SKIP PDF] {url}")
            results.append({
                **url_data,
                "browserbase_content_len": 0,
                "browserbase_success": False,
                "reason": "PDF - use Tavily content",
            })
            continue

        bb_result = browserbase_extract(url)

        results.append({
            **url_data,
            "browserbase_content_len": bb_result.get("content_len", 0),
            "browserbase_success": bb_result.get("success", False),
            "browserbase_preview": bb_result.get("content_preview", ""),
        })

    return results


def main():
    print("=" * 70)
    print("HYBRID APPROACH BENCHMARK")
    print("Tavily Search → Browserbase Extraction")
    print("=" * 70)

    # Test queries
    queries = [
        "CDC clinical guidelines emergency protocols",
        "California medical board telehealth regulations",
    ]

    all_results = []
    for query in queries:
        results = compare_extraction(query)
        all_results.extend(results)

    # Summary
    print("\n\n" + "=" * 70)
    print("COMPARISON SUMMARY")
    print("=" * 70)
    print(f"\n{'Title':<40} {'Tavily':<12} {'Browserbase':<12} {'Winner'}")
    print("-" * 70)

    for r in all_results:
        title = r["title"][:38]
        tavily_kb = r["tavily_content_len"] / 1024
        bb_kb = r["browserbase_content_len"] / 1024

        if not r.get("browserbase_success"):
            winner = "Tavily (BB failed)"
        elif bb_kb > tavily_kb * 1.5:
            winner = "Browserbase"
        elif tavily_kb > bb_kb * 1.5:
            winner = "Tavily"
        else:
            winner = "Similar"

        print(f"{title:<40} {tavily_kb:<12.1f}KB {bb_kb:<12.1f}KB {winner}")

    # Save
    with open("data/tavily_hybrid_benchmark.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to data/tavily_hybrid_benchmark.json")


if __name__ == "__main__":
    main()
