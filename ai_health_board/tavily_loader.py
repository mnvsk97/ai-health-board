"""Tavily + Browserbase hybrid guideline loader for the ADK scenario pipeline.

This module fetches clinical guidelines from the web using:
- Tavily Search: Discovery + PDF extraction
- Browserbase/Stagehand: High-quality HTML extraction (2x more content)

Guidelines are stored as ExtractedGuidelines in Redis for the ADK pipeline to consume.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from loguru import logger
from tavily import TavilyClient

from ai_health_board import redis_store
from ai_health_board.content_validator import get_validator, validate_guideline_content
from ai_health_board.observability import trace_op

load_dotenv()

GuidelineCategory = Literal["general", "specialty", "region", "role"]

# Project root for script paths
PROJECT_ROOT = Path(__file__).parent.parent


# Source configurations based on benchmark results
SOURCES = {
    "general": [
        {
            "name": "CDC",
            "query": "CDC clinical guidelines treatment recommendations",
            "domains": ["cdc.gov"],
        },
        {
            "name": "WHO",
            "query": "WHO clinical practice guidelines",
            "domains": ["who.int"],
        },
    ],
    "specialty": {
        "cardiology": [
            {
                "name": "AHA",
                "query": "American Heart Association clinical guidelines",
                "domains": ["heart.org", "ahajournals.org"],
            },
        ],
        "oncology": [
            {
                "name": "NCCN",
                "query": "NCCN cancer treatment guidelines",
                "domains": ["nccn.org"],
                "use_crawl": True,  # Crawl works on NCCN
                "crawl_url": "https://www.nccn.org/guidelines/category_1",
            },
        ],
        "diabetes": [
            {
                "name": "ADA",
                "query": "American Diabetes Association standards of care",
                "domains": ["diabetes.org", "diabetesjournals.org"],
            },
        ],
    },
    "region": {
        "CA": [
            {
                "name": "CA Medical Board",
                "query": "California medical board telehealth prescribing regulations",
                "domains": ["ca.gov", "mbc.ca.gov"],
            },
        ],
        "TX": [
            {
                "name": "TX Medical Board",
                "query": "Texas medical board practice regulations",
                "domains": ["texas.gov", "tmb.state.tx.us"],
            },
        ],
    },
    "role": {
        "nurse": [
            {
                "name": "AANP",
                "query": "nurse practitioner scope of practice prescribing authority",
                "domains": ["aanp.org"],
            },
        ],
        "pharmacist": [
            {
                "name": "ASHP",
                "query": "pharmacist clinical guidelines prescribing",
                "domains": ["ashp.org"],
            },
        ],
    },
}


class TavilyGuidelineLoader:
    """Loads clinical guidelines using Tavily (discovery/PDFs) + Browserbase (HTML)."""

    def __init__(
        self,
        use_browserbase: bool = True,
        validate_content: bool = True,
        use_llm_validation: bool = True,
    ) -> None:
        """Initialize the loader.

        Args:
            use_browserbase: If True, use Browserbase for HTML extraction (higher quality).
                           If False, use Tavily content only (faster, lower quality).
            validate_content: If True, validate content before storing (filters non-guidelines).
            use_llm_validation: If True, use LLM for ambiguous content classification.
        """
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY environment variable not set")
        self._client = TavilyClient(api_key=api_key)
        self._use_browserbase = use_browserbase
        self._validate_content = validate_content
        self._content_validator = get_validator(use_llm_fallback=use_llm_validation) if validate_content else None

        # Check Browserbase availability
        if use_browserbase:
            bb_key = os.getenv("BROWSERBASE_API_KEY")
            bb_project = os.getenv("BROWSERBASE_PROJECT_ID")
            if not bb_key or not bb_project:
                logger.warning("Browserbase credentials not found, falling back to Tavily-only")
                self._use_browserbase = False

    @trace_op("tavily.search_guidelines")
    def _search_guidelines(
        self,
        query: str,
        domains: list[str] | None = None,
        max_results: int = 10,
    ) -> list[dict]:
        """Search for guidelines using Tavily."""
        result = self._client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_raw_content=True,
            include_domains=domains,
        )
        return result.get("results", [])

    @trace_op("tavily.crawl_guidelines")
    def _crawl_guidelines(
        self,
        url: str,
        instructions: str = "Find clinical guidelines and treatment recommendations",
        limit: int = 20,
    ) -> list[dict]:
        """Crawl a site for guidelines (works on some sites like NCCN)."""
        try:
            result = self._client.crawl(
                url=url,
                max_depth=2,
                limit=limit,
                instructions=instructions,
            )
            return result.get("results", [])
        except Exception:
            # Crawl fails on many sites, return empty
            return []

    @trace_op("browserbase.extract_guideline")
    def _extract_with_browserbase(self, url: str) -> dict | None:
        """Use Browserbase/Stagehand for high-quality structured extraction.

        Returns structured guideline data or None if extraction fails.
        """
        if not self._use_browserbase:
            return None

        script_path = PROJECT_ROOT / "scripts" / "stagehand_extract.mjs"
        if not script_path.exists():
            logger.warning(f"Stagehand script not found: {script_path}")
            return None

        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                output_path = f.name

            result = subprocess.run(
                ["node", str(script_path), "--url", url, "--out", output_path],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(PROJECT_ROOT),
            )

            if result.returncode == 0 and os.path.exists(output_path):
                with open(output_path) as f:
                    data = json.load(f)

                if data and len(data) > 0:
                    guideline = data[0]
                    logger.info(f"Browserbase extracted: {guideline.get('title', 'N/A')[:50]}")

                    # Get raw content for ADK pipeline's LLM
                    raw_content = guideline.get("raw_content", "")

                    return {
                        "source_url": url,
                        "title": guideline.get("title", ""),
                        "condition": guideline.get("condition", ""),
                        "urgency": guideline.get("urgency", "non_emergent"),
                        "red_flags": guideline.get("red_flags", []),
                        "recommendations": guideline.get("recommendations", []),
                        "last_updated": guideline.get("last_updated"),
                        "hash": guideline.get("hash", ""),
                        "extracted_at": guideline.get("extracted_at", time.time()),
                        "extraction_method": "browserbase",
                        "raw_content": raw_content,  # For ADK pipeline's LLM
                        "content_length": len(raw_content),
                    }

            logger.warning(f"Browserbase extraction failed for {url}: {result.stderr[:200]}")
            return None

        except subprocess.TimeoutExpired:
            logger.warning(f"Browserbase timeout for {url}")
            return None
        except Exception as e:
            logger.warning(f"Browserbase error for {url}: {e}")
            return None
        finally:
            # Cleanup temp file
            if "output_path" in locals() and os.path.exists(output_path):
                os.unlink(output_path)

    def _to_extracted_guideline(
        self,
        url: str,
        title: str,
        content: str,
        category: GuidelineCategory,
        subcategory: str | None = None,
    ) -> dict:
        """Convert raw content to ExtractedGuideline format."""
        # Basic urgency detection from content
        content_lower = content.lower()
        if any(kw in content_lower for kw in ["emergency", "immediately", "urgent", "life-threatening"]):
            urgency = "emergent"
        elif any(kw in content_lower for kw in ["soon", "prompt", "timely"]):
            urgency = "conditionally_emergent"
        else:
            urgency = "non_emergent"

        # Extract potential red flags (sentences with warning keywords)
        red_flags = []
        for sentence in content.split("."):
            if any(kw in sentence.lower() for kw in ["warning", "danger", "risk", "avoid", "emergency", "immediately"]):
                cleaned = sentence.strip()[:200]
                if cleaned and len(cleaned) > 20:
                    red_flags.append(cleaned)

        # Extract potential recommendations
        recommendations = []
        for sentence in content.split("."):
            if any(kw in sentence.lower() for kw in ["recommend", "should", "advise", "suggest", "guideline"]):
                cleaned = sentence.strip()[:200]
                if cleaned and len(cleaned) > 20:
                    recommendations.append(cleaned)

        return {
            "source_url": url,
            "title": title[:200] if title else "Untitled",
            "condition": subcategory or category,
            "urgency": urgency,
            "red_flags": red_flags[:10],
            "recommendations": recommendations[:10],
            "last_updated": None,
            "hash": hashlib.sha256(content.encode()).hexdigest()[:32],
            "raw_content": content,  # Preserve for validation
            "extracted_at": time.time(),
            # Extended fields for category filtering
            "category": category,
            "subcategory": subcategory,
            "extraction_method": "tavily",
        }

    @trace_op("tavily.validate_guideline")
    def _validate_and_save(self, guideline: dict) -> bool:
        """Validate guideline content and save to Redis if valid.

        Args:
            guideline: The guideline dict to validate

        Returns:
            True if valid and saved, False if filtered out
        """
        if not self._validate_content or not self._content_validator:
            # Skip validation, just save
            redis_store.save_extracted_guideline(guideline)
            return True

        # Get content for validation
        content = guideline.get("raw_content", "")
        title = guideline.get("title", "")
        url = guideline.get("source_url", "")

        # Validate
        result = self._content_validator.validate_content(content, title, url)

        if result["is_valid"]:
            # Add validation metadata and save
            guideline["_validation_score"] = result["combined_score"]
            guideline["_validation_result"] = result["result"]
            redis_store.save_extracted_guideline(guideline)
            return True
        else:
            logger.info(
                f"Filtered out: {title[:50]}... | "
                f"Reason: {result['reason']} | "
                f"Score: {result['combined_score']:.2f}"
            )
            return False

    @trace_op("tavily.load_category")
    def load_category(
        self,
        category: GuidelineCategory,
        subcategory: str | None = None,
        max_per_source: int = 5,
    ) -> list[dict]:
        """Load guidelines for a category and store in Redis.

        Uses hybrid approach:
        - Tavily Search for discovery and PDF extraction
        - Browserbase for high-quality HTML extraction (2x more content)

        Args:
            category: One of "general", "specialty", "region", "role"
            subcategory: Optional subcategory (e.g., "cardiology", "CA", "nurse")
            max_per_source: Max guidelines to fetch per source

        Returns:
            List of extracted guidelines
        """
        # Get sources for this category
        if category == "general":
            sources = SOURCES["general"]
        else:
            category_sources = SOURCES.get(category, {})
            if subcategory:
                sources = category_sources.get(subcategory, [])
            else:
                # Load all subcategories
                sources = []
                for subcat_sources in category_sources.values():
                    sources.extend(subcat_sources)

        guidelines = []
        stats = {"tavily": 0, "browserbase": 0, "pdf": 0, "crawl": 0, "filtered": 0}

        for source in sources:
            source_name = source["name"]
            logger.info(f"Loading from {source_name}...")

            # Try crawl first if configured (works on NCCN, etc.)
            if source.get("use_crawl") and source.get("crawl_url"):
                results = self._crawl_guidelines(source["crawl_url"], limit=max_per_source)
                for r in results[:max_per_source]:
                    content = r.get("raw_content", "")
                    if content and len(content) > 100:
                        guideline = self._to_extracted_guideline(
                            url=r.get("url", ""),
                            title=r.get("url", "").split("/")[-1],
                            content=content,
                            category=category,
                            subcategory=subcategory or source.get("subcategory"),
                        )
                        guideline["extraction_method"] = "crawl"
                        # Validate and save
                        if self._validate_and_save(guideline):
                            guidelines.append(guideline)
                            stats["crawl"] += 1
                        else:
                            stats["filtered"] += 1

            # Use search for discovery
            results = self._search_guidelines(
                query=source["query"],
                domains=source.get("domains"),
                max_results=max_per_source,
            )

            for r in results:
                url = r.get("url", "")

                # Skip if already loaded via crawl
                if any(g["source_url"] == url for g in guidelines):
                    continue

                tavily_content = r.get("raw_content") or r.get("content", "")
                if not tavily_content or len(tavily_content) < 100:
                    continue

                # Route based on URL type
                is_pdf = url.lower().endswith(".pdf") or "[pdf]" in r.get("title", "").lower()

                if is_pdf:
                    # PDFs: Use Tavily content (Browserbase can't handle PDFs)
                    guideline = self._to_extracted_guideline(
                        url=url,
                        title=r.get("title", ""),
                        content=tavily_content,
                        category=category,
                        subcategory=subcategory or source.get("subcategory"),
                    )
                    guideline["extraction_method"] = "tavily_pdf"
                    stats["pdf"] += 1

                elif self._use_browserbase:
                    # HTML: Try Browserbase first (2x more content, structured)
                    guideline = self._extract_with_browserbase(url)

                    if guideline:
                        # Add category metadata
                        guideline["category"] = category
                        guideline["subcategory"] = subcategory or source.get("subcategory")
                        stats["browserbase"] += 1
                    else:
                        # Fallback to Tavily content
                        guideline = self._to_extracted_guideline(
                            url=url,
                            title=r.get("title", ""),
                            content=tavily_content,
                            category=category,
                            subcategory=subcategory or source.get("subcategory"),
                        )
                        stats["tavily"] += 1
                else:
                    # Browserbase disabled: Use Tavily content
                    guideline = self._to_extracted_guideline(
                        url=url,
                        title=r.get("title", ""),
                        content=tavily_content,
                        category=category,
                        subcategory=subcategory or source.get("subcategory"),
                    )
                    stats["tavily"] += 1

                # Validate and save
                if self._validate_and_save(guideline):
                    guidelines.append(guideline)
                else:
                    stats["filtered"] += 1

            logger.info(f"  {source_name}: {len(guidelines)} guidelines")

        logger.info(
            f"Category {category}/{subcategory or 'all'}: "
            f"{len(guidelines)} valid | "
            f"Filtered: {stats['filtered']} | "
            f"Browserbase: {stats['browserbase']} | "
            f"Tavily: {stats['tavily']} | "
            f"PDF: {stats['pdf']} | "
            f"Crawl: {stats['crawl']}"
        )

        return guidelines

    def load_all(self, max_per_source: int = 5) -> dict[str, int]:
        """Load guidelines from all categories.

        Returns:
            Dict mapping category to count of guidelines loaded
        """
        counts = {}

        # General (baseline)
        guidelines = self.load_category("general", max_per_source=max_per_source)
        counts["general"] = len(guidelines)

        # Specialties
        for specialty in SOURCES.get("specialty", {}).keys():
            guidelines = self.load_category("specialty", specialty, max_per_source)
            counts[f"specialty:{specialty}"] = len(guidelines)

        # Regions
        for region in SOURCES.get("region", {}).keys():
            guidelines = self.load_category("region", region, max_per_source)
            counts[f"region:{region}"] = len(guidelines)

        # Roles
        for role in SOURCES.get("role", {}).keys():
            guidelines = self.load_category("role", role, max_per_source)
            counts[f"role:{role}"] = len(guidelines)

        return counts


# Convenience function for scripts
def load_guidelines(
    category: GuidelineCategory | None = None,
    subcategory: str | None = None,
    max_per_source: int = 5,
    validate_content: bool = True,
    use_llm_validation: bool = True,
) -> list[dict] | dict[str, int]:
    """Load guidelines from Tavily and store in Redis.

    Args:
        category: Specific category to load, or None for all
        subcategory: Specific subcategory (e.g., "cardiology")
        max_per_source: Max guidelines per source
        validate_content: If True, validate content before storing (filters non-guidelines)
        use_llm_validation: If True, use LLM for ambiguous content classification

    Returns:
        List of guidelines if category specified, else dict of counts
    """
    loader = TavilyGuidelineLoader(
        validate_content=validate_content,
        use_llm_validation=use_llm_validation,
    )

    if category:
        return loader.load_category(category, subcategory, max_per_source)
    else:
        return loader.load_all(max_per_source)
