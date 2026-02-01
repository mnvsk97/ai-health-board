"""HTTP-based guideline extractor using direct fetching + LLM extraction."""

from __future__ import annotations

import re
from typing import Any

import httpx
from pydantic import BaseModel, Field

from ai_health_board.observability import trace_op
from ai_health_board.wandb_inference import inference_chat_json


class GuidelineData(BaseModel):
    """Structured data extracted from a clinical guideline page."""

    title: str = Field(description="The guideline title")
    condition: str = Field(description="Medical condition covered")
    urgency: str = Field(
        default="non_emergent",
        description="Urgency level: emergent, conditionally_emergent, or non_emergent",
    )
    red_flags: list[str] = Field(
        default_factory=list,
        description="Warning signs requiring immediate care",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Key clinical recommendations",
    )
    last_updated: str | None = Field(
        default=None,
        description="Date the guideline was last updated",
    )
    source_url: str | None = Field(
        default=None,
        description="URL where the guideline was extracted from",
    )


def _html_to_text(html: str) -> str:
    """Convert HTML to plain text, preserving structure."""
    # Remove script and style elements
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)

    # Convert common elements to text markers
    html = re.sub(r"<h[1-6][^>]*>", "\n\n## ", html, flags=re.IGNORECASE)
    html = re.sub(r"</h[1-6]>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<p[^>]*>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</p>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<br[^>]*>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<li[^>]*>", "\n- ", html, flags=re.IGNORECASE)
    html = re.sub(r"</li>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"</?ul[^>]*>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</?ol[^>]*>", "\n", html, flags=re.IGNORECASE)

    # Remove remaining tags
    html = re.sub(r"<[^>]+>", " ", html)

    # Clean up whitespace
    html = re.sub(r"[ \t]+", " ", html)
    html = re.sub(r"\n\s*\n", "\n\n", html)
    html = html.strip()

    # Decode HTML entities
    html = html.replace("&nbsp;", " ")
    html = html.replace("&amp;", "&")
    html = html.replace("&lt;", "<")
    html = html.replace("&gt;", ">")
    html = html.replace("&quot;", '"')
    html = html.replace("&#39;", "'")

    return html


class HTTPGuidelineExtractor:
    """Extractor for clinical guidelines using HTTP fetching + LLM extraction."""

    def __init__(self, timeout: float = 30.0) -> None:
        """Initialize the HTTP extractor.

        Args:
            timeout: Request timeout in seconds.
        """
        self.timeout = timeout
        self._client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"macOS"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            },
        )

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "HTTPGuidelineExtractor":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    @trace_op("http.fetch")
    def fetch_page(self, url: str) -> str:
        """Fetch a page and convert to text.

        Args:
            url: The URL to fetch.

        Returns:
            Plain text content of the page.
        """
        print(f"Fetching: {url}")
        response = self._client.get(url)
        response.raise_for_status()

        text = _html_to_text(response.text)

        # Truncate if too long (LLM context limits)
        max_chars = 15000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Content truncated...]"

        print(f"Fetched {len(text)} characters")
        return text

    @trace_op("http.extract_guideline")
    def extract_guideline(self, url: str) -> dict[str, Any]:
        """Extract structured guideline data from a URL.

        Args:
            url: URL of the guideline page to extract.

        Returns:
            Dictionary containing extracted guideline data.
        """
        # Fetch the page content
        text = self.fetch_page(url)

        # Use LLM to extract structured data
        print("Extracting guideline data with LLM...")

        prompt = [
            {
                "role": "system",
                "content": """You are a clinical guideline extraction assistant. Extract structured information from healthcare guideline documents.
Always respond with valid JSON matching the requested schema.""",
            },
            {
                "role": "user",
                "content": f"""Extract clinical guideline information from this page content:

{text}

Return a JSON object with these fields:
- title: The guideline title or main heading
- condition: Medical condition or health topic covered (e.g., "childhood immunization", "diabetes management")
- urgency: Classify as 'emergent' (immediate care needed), 'conditionally_emergent' (may need urgent care), or 'non_emergent' (routine/preventive care)
- red_flags: Array of warning signs, danger symptoms, or conditions requiring immediate medical attention
- recommendations: Array of key clinical recommendations, treatment guidelines, or care instructions
- last_updated: Date this content was last updated or reviewed (null if not visible)

Respond only with the JSON object, no additional text.""",
            },
        ]

        result = inference_chat_json(None, prompt)

        # Add the source URL
        result["source_url"] = url

        print(f"Extracted: {result.get('title', 'Unknown')}")
        return result

    @trace_op("http.run")
    def run(self, urls: list[str]) -> list[dict[str, Any]]:
        """Extract guidelines from multiple URLs.

        Args:
            urls: List of URLs to extract.

        Returns:
            List of extracted guideline dictionaries.
        """
        guidelines: list[dict[str, Any]] = []

        for url in urls:
            try:
                guideline = self.extract_guideline(url)
                guidelines.append(guideline)
            except Exception as e:
                print(f"Failed to extract {url}: {e}")

        return guidelines
