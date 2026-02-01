"""Browser agent package for automated guideline discovery."""

from .stagehand_client import StagehandClient
from .cdc_extractor import CDCExtractor, GuidelineData, GuidelineExtractor
from .http_extractor import HTTPGuidelineExtractor
from .change_detector import ChangeDetector

__all__ = [
    "StagehandClient",
    "CDCExtractor",
    "GuidelineExtractor",
    "HTTPGuidelineExtractor",
    "GuidelineData",
    "ChangeDetector",
]
