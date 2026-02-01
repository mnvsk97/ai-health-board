from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class RubricCriterion(BaseModel):
    criterion: str
    points: int = 5
    tags: list[str] = Field(default_factory=list)
    # Compliance-aware fields
    applicable_roles: list[str] | None = None  # ["doctor", "nurse", "pharmacist"]
    compliance_category: str | None = None  # "licensure", "scope", "consent", "hipaa"
    state_specific: str | None = None  # "CA", "TX" - only applies in this state
    is_critical: bool = False  # Auto-fail if score = 0


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
    # Target agent context for compliance checking
    target_agent_role: str | None = None  # "doctor", "nurse", "pharmacist", "receptionist"
    target_agent_specialty: str | None = None  # "cardiology", "family_medicine"
    target_licensed_states: list[str] = Field(default_factory=list)  # ["UT", "NV", "AZ"]
    patient_state: str | None = None  # Where patient is located
    modality: Literal["in_person", "telehealth", "phone"] | None = None


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


class HealthBenchPrompt(BaseModel):
    role: str
    content: str


class HealthBenchItem(BaseModel):
    prompt_id: str
    prompt: list[HealthBenchPrompt]
    rubrics: list[RubricCriterion]
    example_tags: list[str] = Field(default_factory=list)


class ScenarioRequest(BaseModel):
    request_id: str
    source_type: Literal["bench", "web"]
    source_url: str | None = None
    title: str | None = None
    description: str | None = None
    state: str | None = None
    specialty: str | None = None
    rubric_criteria: list[RubricCriterion] = Field(default_factory=list)
    guideline: dict | None = None
    bench_item: HealthBenchItem | None = None
