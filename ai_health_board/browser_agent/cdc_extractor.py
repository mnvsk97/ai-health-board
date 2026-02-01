"""Clinical guidelines extractor using Stagehand browser automation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from ai_health_board.observability import trace_op

if TYPE_CHECKING:
    from .stagehand_client import StagehandClient

CDC_GUIDELINES_URL = "https://www.cdc.gov/clinical-guidance/index.html"


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


class GuidelineExtractor:
    """Extractor for clinical guidelines using Stagehand browser automation."""

    def __init__(self, client: "StagehandClient") -> None:
        """Initialize the extractor with a Stagehand client.

        Args:
            client: Initialized StagehandClient instance.
        """
        self.client = client

    @trace_op("browser.guideline.extract")
    def extract_guideline(self, url: str) -> dict[str, Any]:
        """Extract structured guideline data from a specific URL.

        Args:
            url: URL of the guideline page to extract.

        Returns:
            Dictionary containing extracted guideline data.
        """
        print(f"Navigating to: {url}")
        self.client.navigate(url)

        # Extract structured guideline data using the schema
        print("Extracting guideline data...")
        result = self.client.extract(
            instruction="""Extract clinical guideline information from this page:
            - title: The guideline title or page heading
            - condition: Medical condition or health topic covered
            - urgency: Classify as 'emergent' (immediate care needed), 'conditionally_emergent' (may need urgent care), or 'non_emergent' (routine care)
            - red_flags: List any warning signs, danger symptoms, or conditions requiring immediate medical attention
            - recommendations: List the key clinical recommendations, treatment guidelines, or care instructions
            - last_updated: Extract the date this content was last updated or reviewed if visible""",
            schema=GuidelineData.model_json_schema(),
        )

        # Extract the data from the response
        guideline: dict[str, Any] = {}
        if hasattr(result, "data") and result.data:
            guideline = dict(result.data) if hasattr(result.data, "__iter__") else {}
        elif hasattr(result, "model_dump"):
            guideline = result.model_dump()
        elif hasattr(result, "model_extra"):
            guideline = dict(result.model_extra or {})
        elif isinstance(result, dict):
            guideline = result

        if isinstance(guideline, dict) and "result" in guideline:
            nested = guideline.get("result")
            if isinstance(nested, dict):
                guideline = nested

        # Add the source URL
        guideline["source_url"] = url

        print(f"Extracted: {guideline.get('title', 'Unknown')}")
        return guideline


class CDCExtractor(GuidelineExtractor):
    """Extractor specifically for CDC clinical guidelines."""

    @trace_op("browser.cdc.discover")
    def discover_guideline_links(self, base_url: str = CDC_GUIDELINES_URL) -> list[str]:
        """Discover clinical guideline links from the CDC index page.

        Args:
            base_url: The index page URL to start from.

        Returns:
            List of URLs pointing to clinical guideline pages.
        """
        print(f"Navigating to CDC guidelines index: {base_url}")
        self.client.navigate(base_url)

        # Observe available links
        print("Observing page for guideline links...")
        self.client.observe(
            "Find all links to clinical guidelines and medical recommendations"
        )

        # Extract links to clinical guidelines
        print("Extracting guideline URLs...")
        result = self.client.extract(
            instruction="Extract all URLs that link to clinical guidelines, medical recommendations, or healthcare guidance documents. Return only valid http/https URLs.",
            schema={"type": "array", "items": {"type": "string", "format": "uri"}},
        )

        # Parse the links from the response
        links = []
        if hasattr(result, "data") and result.data:
            links = list(result.data) if hasattr(result.data, "__iter__") else []
        elif isinstance(result, list):
            links = result

        # Filter and validate links
        valid_links = []
        for link in links:
            if isinstance(link, str) and link.startswith("http"):
                valid_links.append(link)

        print(f"Discovered {len(valid_links)} guideline links")
        return valid_links

    @trace_op("browser.cdc.run")
    def run(self, max_guidelines: int = 5) -> list[dict[str, Any]]:
        """Run the full extraction pipeline for CDC guidelines.

        Args:
            max_guidelines: Maximum number of guidelines to extract.

        Returns:
            List of extracted guideline dictionaries.
        """
        guidelines: list[dict[str, Any]] = []

        # Discover guideline links
        links = self.discover_guideline_links()

        # Extract each guideline up to the limit
        for url in links[:max_guidelines]:
            try:
                guideline = self.extract_guideline(url)
                guidelines.append(guideline)
            except Exception as e:
                print(f"Failed to extract {url}: {e}")

        return guidelines
