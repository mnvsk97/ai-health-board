"""Change detection for extracted guidelines using content hashing."""

from __future__ import annotations

import hashlib
from typing import Any, Literal

from ai_health_board import redis_store


class ChangeDetector:
    """Detector for new or updated guidelines using content hashing."""

    def compute_hash(self, guideline: dict[str, Any]) -> str:
        """Compute a SHA-256 hash of the guideline content.

        The hash is computed from the title and recommendations to detect
        meaningful content changes while ignoring cosmetic updates.

        Args:
            guideline: Dictionary containing guideline data.

        Returns:
            SHA-256 hex digest of the content.
        """
        title = guideline.get("title", "")
        recommendations = guideline.get("recommendations", [])

        # Normalize recommendations to a string
        if isinstance(recommendations, list):
            recommendations_str = "|".join(str(r) for r in recommendations)
        else:
            recommendations_str = str(recommendations)

        content = f"{title}|{recommendations_str}"
        return hashlib.sha256(content.encode()).hexdigest()

    def is_new_or_updated(
        self, guideline: dict[str, Any]
    ) -> tuple[bool, Literal["new", "updated", "unchanged"]]:
        """Check if a guideline is new or has been updated.

        Compares the computed hash of the guideline against the stored
        version to detect changes.

        Args:
            guideline: Dictionary containing guideline data.

        Returns:
            Tuple of (is_changed, reason) where reason is 'new', 'updated',
            or 'unchanged'.
        """
        source_url = guideline.get("source_url", "")
        if not source_url:
            return True, "new"

        new_hash = self.compute_hash(guideline)

        # Look up existing guideline by URL
        existing = redis_store.get_extracted_guideline_by_url(source_url)

        if not existing:
            return True, "new"

        existing_hash = existing.get("hash", "")
        if existing_hash != new_hash:
            return True, "updated"

        return False, "unchanged"
