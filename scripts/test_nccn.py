#!/usr/bin/env python3
"""Test all approaches on NCCN guidelines site."""

from __future__ import annotations

import json
import os
import subprocess
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

NCCN_URL = "https://www.nccn.org/guidelines/category_1"


def test_tavily_crawl():
    """Test Tavily crawl on NCCN."""
    print("\n" + "=" * 70)
    print("[TAVILY CRAWL] Testing on NCCN...")
    print("=" * 70)

    try:
        result = client.crawl(
            url=NCCN_URL,
            max_depth=2,
            limit=20,
            instructions="Find cancer treatment guidelines and clinical recommendations",
            extract_depth="advanced",
            format="markdown",
        )

        pages = result.get("results", [])
        print(f"\nPages found: {len(pages)}")

        if pages:
            total_content = sum(len(p.get("raw_content", "")) for p in pages)
            print(f"Total content: {total_content:,} chars ({total_content/1024:.1f} KB)")

            print("\nURLs discovered:")
            for p in pages[:10]:
                url = p.get("url", "")
                content_len = len(p.get("raw_content", ""))
                print(f"  - {url[:70]} ({content_len:,} chars)")

            # Show sample content
            if pages[0].get("raw_content"):
                print(f"\nSample content from first page:")
                print(pages[0]["raw_content"][:500])

        return {
            "method": "crawl",
            "pages": len(pages),
            "total_kb": sum(len(p.get("raw_content", "")) for p in pages) / 1024,
            "urls": [p.get("url", "") for p in pages],
        }

    except Exception as e:
        print(f"ERROR: {e}")
        return {"method": "crawl", "pages": 0, "error": str(e)}


def test_tavily_search():
    """Test Tavily search for NCCN content."""
    print("\n" + "=" * 70)
    print("[TAVILY SEARCH] Testing NCCN-focused search...")
    print("=" * 70)

    try:
        result = client.search(
            query="NCCN cancer treatment guidelines clinical recommendations",
            search_depth="advanced",
            max_results=10,
            include_raw_content=True,
            include_domains=["nccn.org"],
        )

        results = result.get("results", [])
        print(f"\nResults found: {len(results)}")

        total_content = sum(len(r.get("raw_content") or "") for r in results)
        print(f"Total content: {total_content:,} chars ({total_content/1024:.1f} KB)")

        print("\nURLs found:")
        for r in results[:10]:
            url = r.get("url", "")
            title = r.get("title", "")[:50]
            content_len = len(r.get("raw_content") or "")
            print(f"  - {title} ({content_len:,} chars)")
            print(f"    {url[:70]}")

        # Show sample content
        if results and results[0].get("raw_content"):
            print(f"\nSample content from first result:")
            print(results[0]["raw_content"][:500])

        return {
            "method": "search",
            "pages": len(results),
            "total_kb": total_content / 1024,
            "urls": [r.get("url", "") for r in results],
        }

    except Exception as e:
        print(f"ERROR: {e}")
        return {"method": "search", "pages": 0, "error": str(e)}


def test_tavily_map():
    """Test Tavily map on NCCN."""
    print("\n" + "=" * 70)
    print("[TAVILY MAP] Testing on NCCN...")
    print("=" * 70)

    try:
        result = client.map(
            url=NCCN_URL,
            max_depth=2,
            limit=50,
        )

        urls = result.get("urls", [])
        print(f"\nURLs discovered: {len(urls)}")

        if urls:
            print("\nSample URLs:")
            for url in urls[:15]:
                print(f"  - {url[:80]}")

        return {
            "method": "map",
            "urls_found": len(urls),
            "urls": urls[:20],
        }

    except Exception as e:
        print(f"ERROR: {e}")
        return {"method": "map", "urls_found": 0, "error": str(e)}


def test_browserbase():
    """Test Browserbase extraction on NCCN."""
    print("\n" + "=" * 70)
    print("[BROWSERBASE] Testing on NCCN...")
    print("=" * 70)

    try:
        result = subprocess.run(
            ["node", "scripts/stagehand_raw_extract.mjs", NCCN_URL],
            capture_output=True,
            text=True,
            timeout=90,
            cwd="/Users/saikrishna/dev/ai-health-board",
        )

        # Parse JSON from output
        lines = result.stdout.strip().split("\n")
        json_line = None
        for line in reversed(lines):
            if line.strip().startswith("{"):
                json_line = line
                break

        if json_line:
            data = json.loads(json_line)
            content = data.get("content", "")
            print(f"\nContent extracted: {len(content):,} chars ({len(content)/1024:.1f} KB)")
            print(f"Title: {data.get('title', 'N/A')}")

            if content:
                print(f"\nSample content:")
                print(content[:500])

            return {
                "method": "browserbase",
                "content_kb": len(content) / 1024,
                "title": data.get("title", ""),
                "content_preview": content[:1000] if content else "",
            }
        else:
            print(f"No JSON output. Stderr: {result.stderr[:500]}")
            return {"method": "browserbase", "content_kb": 0, "error": "No JSON output"}

    except subprocess.TimeoutExpired:
        print("TIMEOUT after 90s")
        return {"method": "browserbase", "content_kb": 0, "error": "Timeout"}
    except Exception as e:
        print(f"ERROR: {e}")
        return {"method": "browserbase", "content_kb": 0, "error": str(e)}


def main():
    print("=" * 70)
    print(f"NCCN GUIDELINES EXTRACTION TEST")
    print(f"URL: {NCCN_URL}")
    print("=" * 70)

    results = []

    # Test all approaches
    results.append(test_tavily_crawl())
    results.append(test_tavily_search())
    results.append(test_tavily_map())
    results.append(test_browserbase())

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for r in results:
        method = r.get("method", "unknown")
        if "error" in r:
            print(f"{method:<15}: ERROR - {r['error'][:50]}")
        elif method == "map":
            print(f"{method:<15}: {r.get('urls_found', 0)} URLs discovered")
        elif method == "browserbase":
            print(f"{method:<15}: {r.get('content_kb', 0):.1f} KB content")
        else:
            print(f"{method:<15}: {r.get('pages', 0)} pages, {r.get('total_kb', 0):.1f} KB content")

    # Save results
    with open("data/nccn_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to data/nccn_test_results.json")


if __name__ == "__main__":
    main()
