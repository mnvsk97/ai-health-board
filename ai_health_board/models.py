from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class RubricCriterion(BaseModel):
    criterion: str
    points: int = 5
    tags: list[str] = Field(default_factory=list)


class Scenario(BaseModel):
    scenario_id: str
    title: str
    description: str
    source_type: Literal["bench", "web", "trace", "performance"]
    source_url: str | None = None
    state: str | None = None
    specialty: str | None = None
    rubric_criteria: list[RubricCriterion]
    clinician_approved: bool = True


class TranscriptEntry(BaseModel):
    role: Literal["tester", "target", "system"]
    content: str
    timestamp: float


class Run(BaseModel):
    run_id: str
    status: Literal["pending", "running", "grading", "completed", "failed", "canceled"]
    scenario_ids: list[str]
    mode: Literal["text_text", "text_voice", "voice_voice"]
    room_url: str | None = None
    room_name: str | None = None
    room_token: str | None = None
    started_at: float | None = None
    updated_at: float | None = None


class GradingResult(BaseModel):
    grader_model: str
    break_type: str
    severity: Literal["critical", "high", "medium", "low"]
    evaluations: list[dict]


class Guideline(BaseModel):
    guideline_id: str
    source_url: str
    state: str | None = None
    specialty: str | None = None
    version: str
    hash: str
    last_checked: float


class ComplianceStatus(BaseModel):
    target_id: str
    status: Literal["valid", "outdated", "pending"]
    reason: str | None = None
    updated_at: float


class ExtractedGuideline(BaseModel):
    """Guideline data extracted from a clinical guidelines source."""

    source_url: str
    title: str
    condition: str
    urgency: Literal["emergent", "conditionally_emergent", "non_emergent"] = "non_emergent"
    red_flags: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    last_updated: str | None = None
    hash: str
    extracted_at: float
