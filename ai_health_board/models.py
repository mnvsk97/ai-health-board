from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


# =============================================================================
# Intake Agent Models
# =============================================================================


class PatientIdentity(BaseModel):
    """Patient identity information for verification."""

    first_name: str
    last_name: str
    date_of_birth: str  # ISO format YYYY-MM-DD
    ssn_last_four: str | None = None
    patient_id: str | None = None
    verified: bool = False
    verification_method: str | None = None
    match_confidence: float | None = None


class InsuranceInfo(BaseModel):
    """Patient insurance information."""

    carrier_name: str
    member_id: str
    group_number: str | None = None
    subscriber_name: str | None = None
    subscriber_dob: str | None = None
    relationship_to_subscriber: Literal["self", "spouse", "child", "other"] = "self"
    eligibility_verified: bool = False
    copay_amount: float | None = None
    deductible_remaining: float | None = None


class PatientDemographics(BaseModel):
    """Patient demographic information."""

    street_address: str
    city: str
    state: str
    zip_code: str
    phone_number: str
    email: str | None = None
    preferred_contact_method: Literal["phone", "email", "text"] = "phone"
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    emergency_contact_relationship: str | None = None


class TriageAssessment(BaseModel):
    """Clinical triage assessment results."""

    chief_complaint: str
    symptoms: list[str] = Field(default_factory=list)
    symptom_duration: str | None = None
    symptom_severity: Literal["mild", "moderate", "severe"] | None = None
    acuity_level: Literal["emergent", "urgent", "semi_urgent", "non_urgent"] = "non_urgent"
    is_emergency: bool = False
    emergency_type: str | None = None
    red_flags: list[str] = Field(default_factory=list)
    recommended_action: str | None = None
    call_911: bool = False


class AppointmentSlot(BaseModel):
    """Available appointment slot."""

    slot_id: str
    provider_name: str
    provider_specialty: str
    location: str
    date: str  # ISO format YYYY-MM-DD
    time: str  # HH:MM format
    duration_minutes: int = 30
    appointment_type: Literal["new_patient", "follow_up", "urgent", "telehealth"] = "new_patient"
    available: bool = True


class AppointmentBooking(BaseModel):
    """Booked appointment details."""

    appointment_id: str
    slot_id: str
    patient_id: str
    provider_name: str
    provider_specialty: str
    location: str
    date: str
    time: str
    duration_minutes: int
    appointment_type: str
    reason: str
    confirmation_sent: bool = False
    confirmation_method: Literal["phone", "email", "text"] | None = None


class IntakeSession(BaseModel):
    """Complete intake session tracking all workflow stages."""

    session_id: str
    current_stage: Literal[
        "greeting",
        "consent",
        "identity",
        "insurance",
        "demographics",
        "triage",
        "scheduling",
        "confirmation",
        "completed",
        "emergency_escalation",
    ] = "greeting"
    consent_obtained: bool = False
    patient_identity: PatientIdentity | None = None
    insurance_info: InsuranceInfo | None = None
    demographics: PatientDemographics | None = None
    triage_assessment: TriageAssessment | None = None
    appointment: AppointmentBooking | None = None
    started_at: float
    updated_at: float
    completed_at: float | None = None
    notes: list[str] = Field(default_factory=list)


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


class ScenarioResult(BaseModel):
    """Result of running a single scenario in a batch."""

    run_id: str
    scenario_id: str
    status: Literal["completed", "failed", "canceled"]
    error: str | None = None
    started_at: float
    completed_at: float


class BatchRun(BaseModel):
    """A batch run containing multiple parallel scenario executions."""

    batch_id: str
    status: Literal["pending", "running", "completed", "failed", "canceled"]
    scenario_ids: list[str]
    child_run_ids: list[str] = Field(default_factory=list)
    concurrency: int = 10
    agent_type: str = "intake"
    turns: int = 3
    total_scenarios: int
    completed_count: int = 0
    failed_count: int = 0
    canceled_count: int = 0
    started_at: float | None = None
    completed_at: float | None = None
    created_at: float | None = None
