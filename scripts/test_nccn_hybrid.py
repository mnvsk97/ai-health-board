#!/usr/bin/env python3
"""Test hybrid: Tavily crawl URLs → Browserbase structured extraction."""

from __future__ import annotations

import json
import os
import subprocess
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# URLs discovered by crawl
CRAWL_URLS = [
    "https://www.nccn.org/guidelines/guidelines-detail?category=1&id=1450",  # Non-Small Cell Lung Cancer
    "https://www.nccn.org/guidelines/guidelines-detail?id=1419",  # Breast Cancer
]

def extract_with_stagehand(url: str) -> dict:
    """Use Stagehand structured extraction."""
    print(f"\n[STAGEHAND] {url[:60]}...")

    try:
        result = subprocess.run(
            ["node", "scripts/stagehand_extract.mjs", "--url", url, "--out", "/tmp/nccn_extract.json"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd="/Users/saikrishna/dev/ai-health-board",
        )

        if result.returncode == 0:
            with open("/tmp/nccn_extract.json") as f:
                data = json.load(f)

            if data and len(data) > 0:
                guideline = data[0]
                print(f"  Title: {guideline.get('title', 'N/A')[:60]}")
                print(f"  Condition: {guideline.get('condition', 'N/A')}")
                print(f"  Urgency: {guideline.get('urgency', 'N/A')}")
                print(f"  Red flags: {len(guideline.get('red_flags', []))} items")
                print(f"  Recommendations: {len(guideline.get('recommendations', []))} items")

                if guideline.get('recommendations'):
                    print(f"  Sample recommendation: {guideline['recommendations'][0][:100]}...")

                return {"success": True, "data": guideline}

        print(f"  Failed: {result.stderr[:200]}")
        return {"success": False, "error": result.stderr[:200]}

    except Exception as e:
        print(f"  Error: {e}")
        return {"success": False, "error": str(e)}


def test_tavily_extract(url: str) -> dict:
    """Use Tavily extract on a specific URL."""
    print(f"\n[TAVILY EXTRACT] {url[:60]}...")

    try:
        result = client.extract(
            urls=[url],
            extract_depth="advanced",
        )

        pages = result.get("results", [])
        if pages:
            content = pages[0].get("raw_content", "")
            print(f"  Content: {len(content):,} chars ({len(content)/1024:.1f} KB)")

            # Check for clinical content markers
            has_recommendations = "recommend" in content.lower()
            has_treatment = "treatment" in content.lower()
            has_diagnosis = "diagnosis" in content.lower()

            print(f"  Has recommendations: {has_recommendations}")
            print(f"  Has treatment info: {has_treatment}")
            print(f"  Has diagnosis info: {has_diagnosis}")

            return {"success": True, "content_kb": len(content)/1024, "content": content[:2000]}

        return {"success": False, "error": "No content"}

    except Exception as e:
        print(f"  Error: {e}")
        return {"success": False, "error": str(e)}


def main():
    print("=" * 70)
    print("NCCN HYBRID EXTRACTION TEST")
    print("Testing: Crawl URLs → Structured Extraction")
    print("=" * 70)

    for url in CRAWL_URLS:
        print(f"\n{'='*70}")
        print(f"URL: {url}")
        print("=" * 70)

        # Test Tavily Extract
        tavily_result = test_tavily_extract(url)

        # Test Stagehand structured extraction
        stagehand_result = extract_with_stagehand(url)

        print(f"\nComparison for this URL:")
        print(f"  Tavily Extract: {'✅' if tavily_result.get('success') else '❌'} {tavily_result.get('content_kb', 0):.1f} KB")
        print(f"  Stagehand:      {'✅' if stagehand_result.get('success') else '❌'} Structured data")


if __name__ == "__main__":
    main()
