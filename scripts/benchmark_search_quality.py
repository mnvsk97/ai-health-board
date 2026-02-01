#!/usr/bin/env python3
"""Deep dive on search quality - compare raw content vs extract."""

from __future__ import annotations

import json
import os
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

QUERIES = [
    ("general", "CDC clinical guidelines emergency protocols"),
    ("specialty", "cardiology heart failure treatment guidelines 2024"),
    ("region", "California medical board telemedicine regulations"),
    ("role", "nurse practitioner scope of practice prescribing authority"),
]


def analyze_search_content(query: str, category: str):
    """Analyze what search returns with raw content."""
    print(f"\n{'='*70}")
    print(f"Category: {category}")
    print(f"Query: {query}")
    print('='*70)

    # Search with raw content
    result = client.search(
        query=query,
        search_depth="advanced",
        max_results=5,
        include_raw_content=True,
    )

    results = result.get("results", [])

    print(f"\nFound {len(results)} results\n")

    analysis = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "No title")[:70]
        url = r.get("url", "")
        content_snippet = r.get("content", "")  # Short snippet
        raw_content = r.get("raw_content", "")  # Full content

        snippet_len = len(content_snippet)
        raw_len = len(raw_content)

        print(f"{i}. {title}")
        print(f"   URL: {url[:80]}")
        print(f"   Snippet: {snippet_len:,} chars | Raw: {raw_len:,} chars")

        # Analyze raw content quality
        if raw_content:
            # Check for key indicators of guideline content
            has_recommendations = any(kw in raw_content.lower() for kw in
                ["recommend", "should", "must", "guideline", "protocol"])
            has_red_flags = any(kw in raw_content.lower() for kw in
                ["emergency", "urgent", "warning", "danger", "immediately"])
            has_clinical = any(kw in raw_content.lower() for kw in
                ["patient", "treatment", "diagnosis", "symptoms", "clinical"])

            quality_score = sum([has_recommendations, has_red_flags, has_clinical])
            quality_label = ["Low", "Medium", "Good", "Excellent"][quality_score]

            print(f"   Quality: {quality_label} (recs:{has_recommendations}, flags:{has_red_flags}, clinical:{has_clinical})")

            # Sample of content
            sample = raw_content[:300].replace('\n', ' ').strip()
            print(f"   Sample: {sample}...")

            analysis.append({
                "title": title,
                "url": url,
                "snippet_len": snippet_len,
                "raw_len": raw_len,
                "quality_score": quality_score,
                "has_recommendations": has_recommendations,
                "has_red_flags": has_red_flags,
                "has_clinical": has_clinical,
            })
        else:
            print(f"   ⚠️  No raw content returned")
            analysis.append({
                "title": title,
                "url": url,
                "snippet_len": snippet_len,
                "raw_len": 0,
                "quality_score": 0,
            })

        print()

    return {
        "category": category,
        "query": query,
        "results": analysis,
        "total_raw_kb": sum(a["raw_len"] for a in analysis) / 1024,
        "avg_quality": sum(a["quality_score"] for a in analysis) / len(analysis) if analysis else 0,
    }


def main():
    print("=" * 70)
    print("SEARCH CONTENT QUALITY ANALYSIS")
    print("Checking what search returns with include_raw_content=True")
    print("=" * 70)

    all_results = []
    for category, query in QUERIES:
        result = analyze_search_content(query, category)
        all_results.append(result)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\n{'Category':<15} {'Total KB':<12} {'Avg Quality':<12} {'Analysis'}")
    print("-" * 70)

    for r in all_results:
        total_kb = r["total_raw_kb"]
        avg_q = r["avg_quality"]
        if total_kb > 100 and avg_q >= 2:
            analysis = "✅ EXCELLENT - Rich guideline content"
        elif total_kb > 50 and avg_q >= 1.5:
            analysis = "✅ GOOD - Usable content"
        elif total_kb > 0:
            analysis = "⚠️  LIMITED - Some content but thin"
        else:
            analysis = "❌ POOR - No raw content"

        print(f"{r['category']:<15} {total_kb:<12.1f} {avg_q:<12.1f} {analysis}")

    # Save
    with open("data/tavily_search_quality.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to data/tavily_search_quality.json")


if __name__ == "__main__":
    main()
