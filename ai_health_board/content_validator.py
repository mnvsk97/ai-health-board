"""Content validation for clinical guideline ingestion.

Filters out non-guideline content using:
1. Clinical keyword detection
2. Structured format checks
3. LLM classification for ambiguous cases
"""

from __future__ import annotations

import re
from typing import Any, Literal

from loguru import logger

from ai_health_board.observability import trace_op
from ai_health_board.wandb_inference import inference_chat_json

# Clinical keywords that indicate guideline content
CLINICAL_KEYWORDS = {
    # Treatment/Management
    "treatment", "therapy", "management", "intervention", "medication",
    "drug", "dosage", "dose", "administer", "prescribe", "prescription",
    # Diagnosis
    "diagnosis", "diagnostic", "assessment", "evaluation", "screening",
    "symptom", "sign", "indication", "contraindication",
    # Clinical terms
    "patient", "clinical", "medical", "healthcare", "physician",
    "practitioner", "nurse", "provider", "hospital", "clinic",
    # Guidelines/Standards
    "guideline", "recommendation", "protocol", "standard", "criteria",
    "best practice", "evidence-based", "consensus", "grade",
    # Conditions
    "disease", "disorder", "condition", "syndrome", "infection",
    "chronic", "acute", "emergency", "urgent",
    # Actions
    "monitor", "follow-up", "refer", "consult", "counsel", "educate",
    "prevent", "risk", "complication",
}

# Keywords that indicate non-guideline content (noise)
NOISE_KEYWORDS = {
    "login", "sign in", "register", "subscribe", "newsletter",
    "cookie", "privacy policy", "terms of service", "advertisement",
    "click here", "buy now", "add to cart", "checkout", "payment",
    "contact us", "about us", "careers", "jobs", "footer",
    "copyright", "all rights reserved", "trademark",
    "social media", "follow us", "share this", "tweet",
}

# Structural patterns in clinical guidelines
STRUCTURE_PATTERNS = [
    r"(?i)\b(recommendation|grade)\s*[:\-]?\s*[A-D1-4]",  # Graded recommendations
    r"(?i)\b(step|stage|phase)\s+\d",  # Staged protocols
    r"(?i)\b(first|second|third)[\-\s]line\b",  # Treatment lines
    r"(?i)\b(category|class|level)\s+[IVX1-4]+",  # Classification levels
    r"(?i)\b(table|figure|algorithm)\s+\d",  # Clinical tables/figures
    r"(?i)\bcontraindicated?\b",  # Contraindications
    r"(?i)\bdosage\s*[:\-]",  # Dosage information
    r"(?i)\b(mg|mcg|ml|kg|units?)\b",  # Medical units
    r"(?i)\b(daily|twice|three times|every|q\d+h)\b",  # Frequency patterns
    r"(?i)\b(initial|maintenance|maximum|minimum)\s+(dose|therapy)\b",  # Dose types
]

ValidationResult = Literal["valid", "invalid", "ambiguous"]


class ContentValidator:
    """Validates content for clinical guideline relevance."""

    def __init__(self, use_llm_fallback: bool = True) -> None:
        """Initialize validator.

        Args:
            use_llm_fallback: If True, use LLM classification for ambiguous content
        """
        self._use_llm_fallback = use_llm_fallback

    @trace_op("validator.keyword_score")
    def _calculate_keyword_score(self, content: str) -> dict[str, Any]:
        """Calculate clinical vs noise keyword score.

        Returns:
            Dict with clinical_count, noise_count, and score (-1 to 1)
        """
        content_lower = content.lower()
        words = set(re.findall(r"\b\w+\b", content_lower))

        clinical_count = sum(1 for kw in CLINICAL_KEYWORDS if kw in content_lower)
        noise_count = sum(1 for kw in NOISE_KEYWORDS if kw in content_lower)

        # Normalize by content length (per 1000 chars)
        content_len = max(len(content), 1)
        clinical_density = (clinical_count / content_len) * 1000
        noise_density = (noise_count / content_len) * 1000

        # Score: positive = clinical, negative = noise
        if clinical_density + noise_density == 0:
            score = 0.0
        else:
            score = (clinical_density - noise_density) / (clinical_density + noise_density + 0.1)

        return {
            "clinical_count": clinical_count,
            "noise_count": noise_count,
            "clinical_density": clinical_density,
            "noise_density": noise_density,
            "score": score,
        }

    @trace_op("validator.structure_score")
    def _calculate_structure_score(self, content: str) -> dict[str, Any]:
        """Check for clinical guideline structural patterns.

        Returns:
            Dict with pattern_count, patterns_found, and score (0 to 1)
        """
        patterns_found = []
        for pattern in STRUCTURE_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                patterns_found.append(pattern[:30])

        # Score based on pattern count (0-10 patterns mapped to 0-1)
        score = min(len(patterns_found) / 5.0, 1.0)

        return {
            "pattern_count": len(patterns_found),
            "patterns_found": patterns_found[:5],
            "score": score,
        }

    @trace_op("validator.length_check")
    def _check_content_length(self, content: str) -> dict[str, Any]:
        """Check if content has appropriate length.

        Returns:
            Dict with length, word_count, and is_appropriate
        """
        content_len = len(content)
        word_count = len(content.split())

        # Guidelines typically have substantial content
        is_appropriate = content_len >= 500 and word_count >= 100

        return {
            "length": content_len,
            "word_count": word_count,
            "is_appropriate": is_appropriate,
        }

    @trace_op("validator.llm_classify")
    def _llm_classify(self, content: str, title: str = "") -> dict[str, Any]:
        """Use LLM to classify ambiguous content.

        Returns:
            Dict with is_guideline, confidence, and reason
        """
        # Truncate content for LLM
        content_sample = content[:3000]

        prompt = f"""Analyze this content and determine if it's a clinical/medical guideline.

TITLE: {title or 'Unknown'}

CONTENT SAMPLE:
{content_sample}

A clinical guideline should contain:
- Specific treatment recommendations
- Diagnostic criteria or protocols
- Evidence-based medical advice
- Standard of care information

NOT guidelines: news articles, general health info, product pages, login pages, navigation menus.

Return JSON:
{{
    "is_guideline": true/false,
    "confidence": 0.0-1.0,
    "reason": "Brief explanation",
    "guideline_type": "treatment|diagnostic|prevention|screening|management|null"
}}
"""

        try:
            result = inference_chat_json(
                None,
                [
                    {"role": "system", "content": "You are a medical content classifier."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )

            return {
                "is_guideline": result.get("is_guideline", False),
                "confidence": result.get("confidence", 0.5),
                "reason": result.get("reason", ""),
                "guideline_type": result.get("guideline_type"),
            }

        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")
            return {
                "is_guideline": False,
                "confidence": 0.0,
                "reason": f"Classification error: {e}",
                "guideline_type": None,
            }

    @trace_op("validator.validate_content")
    def validate_content(
        self,
        content: str,
        title: str = "",
        url: str = "",
    ) -> dict[str, Any]:
        """Validate if content is a clinical guideline.

        Args:
            content: The content to validate
            title: Optional title for context
            url: Optional URL for context

        Returns:
            Dict with:
                - is_valid: bool
                - result: "valid" | "invalid" | "ambiguous"
                - scores: keyword, structure, length scores
                - llm_result: LLM classification if used
                - reason: Human-readable explanation
        """
        # Calculate scores
        keyword_scores = self._calculate_keyword_score(content)
        structure_scores = self._calculate_structure_score(content)
        length_check = self._check_content_length(content)

        # Decision logic
        combined_score = (
            keyword_scores["score"] * 0.4
            + structure_scores["score"] * 0.4
            + (0.2 if length_check["is_appropriate"] else 0.0)
        )

        # Clear cases
        if combined_score >= 0.6:
            result = "valid"
            is_valid = True
            reason = f"High clinical content (score: {combined_score:.2f})"
            llm_result = None

        elif combined_score <= 0.1 or keyword_scores["noise_count"] > keyword_scores["clinical_count"] * 2:
            result = "invalid"
            is_valid = False
            reason = f"Non-clinical content (score: {combined_score:.2f}, noise keywords: {keyword_scores['noise_count']})"
            llm_result = None

        elif not length_check["is_appropriate"]:
            result = "invalid"
            is_valid = False
            reason = f"Content too short ({length_check['word_count']} words)"
            llm_result = None

        else:
            # Ambiguous - use LLM if enabled
            if self._use_llm_fallback:
                llm_result = self._llm_classify(content, title)
                is_valid = llm_result["is_guideline"] and llm_result["confidence"] >= 0.7
                result = "valid" if is_valid else "invalid"
                reason = llm_result["reason"]
            else:
                result = "ambiguous"
                is_valid = False
                reason = f"Ambiguous content (score: {combined_score:.2f}), LLM disabled"
                llm_result = None

        logger.debug(
            f"Validated '{title[:30]}...': {result} - {reason} | "
            f"keywords={keyword_scores['clinical_count']}/{keyword_scores['noise_count']} | "
            f"patterns={structure_scores['pattern_count']}"
        )

        return {
            "is_valid": is_valid,
            "result": result,
            "combined_score": combined_score,
            "scores": {
                "keyword": keyword_scores,
                "structure": structure_scores,
                "length": length_check,
            },
            "llm_result": llm_result,
            "reason": reason,
        }


# Singleton instance
_validator: ContentValidator | None = None


def get_validator(use_llm_fallback: bool = True) -> ContentValidator:
    """Get or create the content validator singleton."""
    global _validator
    if _validator is None:
        _validator = ContentValidator(use_llm_fallback=use_llm_fallback)
    return _validator


def validate_guideline_content(
    content: str,
    title: str = "",
    url: str = "",
    use_llm: bool = True,
) -> bool:
    """Convenience function to validate guideline content.

    Args:
        content: The content to validate
        title: Optional title
        url: Optional URL
        use_llm: Whether to use LLM for ambiguous cases

    Returns:
        True if content is a valid clinical guideline
    """
    validator = get_validator(use_llm_fallback=use_llm)
    result = validator.validate_content(content, title, url)
    return result["is_valid"]


def filter_guidelines(
    guidelines: list[dict[str, Any]],
    use_llm: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Filter a list of guidelines, returning valid and invalid separately.

    Args:
        guidelines: List of guideline dicts with 'raw_content' or 'content' field
        use_llm: Whether to use LLM for ambiguous cases

    Returns:
        Tuple of (valid_guidelines, invalid_guidelines)
    """
    validator = get_validator(use_llm_fallback=use_llm)
    valid = []
    invalid = []

    for g in guidelines:
        content = g.get("raw_content") or g.get("content", "")
        title = g.get("title", "")
        url = g.get("source_url", "")

        result = validator.validate_content(content, title, url)

        # Add validation metadata
        g["_validation"] = {
            "is_valid": result["is_valid"],
            "result": result["result"],
            "score": result["combined_score"],
            "reason": result["reason"],
        }

        if result["is_valid"]:
            valid.append(g)
        else:
            invalid.append(g)
            logger.info(f"Filtered out: {title[:50]} - {result['reason']}")

    logger.info(f"Content validation: {len(valid)} valid, {len(invalid)} filtered out")
    return valid, invalid
