"""Integration tests for intake agent conversation flows."""

from __future__ import annotations

import time

import pytest

from ai_health_board.agents.intake_agent import INTAKE_PROMPT, make_intake_agent
from ai_health_board.agents.tools import (
    assess_symptom_urgency,
    book_appointment,
    check_emergency_indicators,
    check_emergency_symptoms,
    get_available_slots,
    get_triage_recommendation,
    verify_insurance_eligibility,
    verify_patient_identity,
)
from ai_health_board.models import IntakeSession, PatientIdentity


class TestIntakeAgentCreation:
    """Tests for intake agent instantiation."""

    def test_make_intake_agent(self) -> None:
        """Test that intake agent is created with correct config."""
        agent = make_intake_agent()
        assert agent["agent_name"] == "intake-agent"
        assert agent["system_prompt"] == INTAKE_PROMPT

    def test_prompt_contains_emergency_protocol(self) -> None:
        """Verify system prompt includes emergency escalation guidance."""
        assert "EMERGENCY ESCALATION" in INTAKE_PROMPT
        assert "911" in INTAKE_PROMPT
        assert "chest pain" in INTAKE_PROMPT.lower()
        assert "difficulty breathing" in INTAKE_PROMPT.lower()

    def test_prompt_contains_privacy_guidelines(self) -> None:
        """Verify system prompt includes privacy guidance."""
        assert "PRIVACY" in INTAKE_PROMPT
        assert "confidential" in INTAKE_PROMPT.lower()

    def test_prompt_contains_workflow_stages(self) -> None:
        """Verify system prompt includes all workflow stages."""
        required_stages = [
            "IDENTITY",
            "INSURANCE",
            "DEMOGRAPHICS",
            "TRIAGE",
            "SCHEDULING",
        ]
        for stage in required_stages:
            assert stage in INTAKE_PROMPT, f"Missing stage: {stage}"


class TestCompleteIntakeFlow:
    """Tests for complete intake conversation flows."""

    def test_new_patient_intake_flow(self) -> None:
        """Test complete flow for a new patient."""
        # 1. Identity verification
        identity_result = verify_patient_identity(
            first_name="Alice",
            last_name="Johnson",
            date_of_birth="1988-09-22",
        )
        assert identity_result["verified"] is True
        patient_id = identity_result["patient_id"]

        # 2. Insurance verification
        insurance_result = verify_insurance_eligibility(
            carrier_name="Blue Cross Blue Shield",
            member_id="XYZ789012",
            group_number="GRP456",
        )
        assert insurance_result["eligible"] is True

        # 3. Triage assessment (non-emergency)
        triage_result = assess_symptom_urgency(
            chief_complaint="persistent headaches",
            symptoms=["pain behind eyes", "sensitivity to light"],
            severity="moderate",
            duration="2 weeks",
        )
        assert triage_result["is_emergency"] is False
        assert triage_result["acuity_level"] in ["semi_urgent", "urgent"]

        # 4. Get recommendation
        recommendation = get_triage_recommendation(
            acuity_level=triage_result["acuity_level"],
            chief_complaint="persistent headaches",
        )
        assert recommendation["appointment_needed"] is True

        # 5. Schedule appointment
        slots = get_available_slots(
            specialty="neurology",
            appointment_type="new_patient",
        )
        assert slots["total_available"] > 0

        booking = book_appointment(
            slot_id=slots["slots"][0]["slot_id"],
            patient_id=patient_id,
            reason="persistent headaches - moderate severity",
        )
        assert booking["success"] is True
        assert "confirmation_number" in booking

    def test_returning_patient_with_urgent_symptoms(self) -> None:
        """Test flow for returning patient with urgent symptoms."""
        # 1. Verify identity with more confidence for returning patient
        identity_result = verify_patient_identity(
            first_name="Bob",
            last_name="Smith",
            date_of_birth="1975-03-15",
            ssn_last_four="5678",
        )
        assert identity_result["verified"] is True
        assert identity_result["match_confidence"] >= 0.9

        # 2. Triage - urgent but not emergency
        triage_result = assess_symptom_urgency(
            chief_complaint="severe abdominal pain",
            symptoms=["nausea", "bloating"],
            severity="severe",
            duration="started yesterday",
        )
        assert triage_result["is_emergency"] is False
        assert triage_result["acuity_level"] == "urgent"

        # 3. Get urgent appointment
        recommendation = get_triage_recommendation(
            acuity_level="urgent",
            chief_complaint="severe abdominal pain",
        )
        assert recommendation["action"] == "same_day_appointment"


class TestEmergencyEscalationFlow:
    """Tests for emergency escalation scenarios."""

    def test_chest_pain_emergency_flow(self) -> None:
        """Test that chest pain triggers immediate emergency escalation."""
        # Simulate patient mentioning chest pain during triage
        emergency_check = check_emergency_symptoms("I'm having chest pain")
        assert emergency_check["is_emergency"] is True
        assert emergency_check["call_911"] is True

        # Detailed emergency indicators check
        indicators = check_emergency_indicators(
            symptoms="chest pain radiating to left arm, sweating",
            age=55,
            medical_history=["high blood pressure"],
        )
        assert indicators["is_emergency"] is True
        assert indicators["do_not_delay"] is True

        # Should not proceed to scheduling
        recommendation = get_triage_recommendation(
            acuity_level="emergent",
            chief_complaint="chest pain",
            is_emergency=True,
        )
        assert recommendation["appointment_needed"] is False
        assert "911" in recommendation["message"]

    def test_stroke_symptoms_emergency_flow(self) -> None:
        """Test stroke symptoms trigger emergency."""
        # Test face drooping (exact keyword match)
        emergency_check = check_emergency_symptoms("I have face drooping on one side")
        assert emergency_check["is_emergency"] is True
        assert emergency_check["emergency_type"] == "face drooping"

        # Test arm weakness (exact keyword match)
        emergency_check2 = check_emergency_symptoms("experiencing arm weakness")
        assert emergency_check2["is_emergency"] is True
        assert emergency_check2["emergency_type"] == "arm weakness"

        # Test slurred speech
        emergency_check3 = check_emergency_symptoms("my speech is slurred speech is hard")
        assert emergency_check3["is_emergency"] is True
        assert emergency_check3["emergency_type"] == "slurred speech"

    def test_breathing_difficulty_emergency_flow(self) -> None:
        """Test breathing difficulty triggers emergency."""
        emergency_check = check_emergency_symptoms(
            "I can't breathe, it's really hard to breathe"
        )
        assert emergency_check["is_emergency"] is True
        assert emergency_check["call_911"] is True

    def test_mental_health_crisis_flow(self) -> None:
        """Test mental health crisis triggers appropriate response."""
        emergency_check = check_emergency_symptoms(
            "I'm feeling suicidal and want to end my life"
        )
        assert emergency_check["is_emergency"] is True
        assert emergency_check["emergency_type"] == "mental_health_crisis"
        # Should refer to 988 crisis line, not necessarily 911
        assert emergency_check.get("call_988") is True

    def test_emergency_mid_intake(self) -> None:
        """Test emergency detection mid-conversation."""
        # Start normal intake
        identity = verify_patient_identity(
            first_name="Carol",
            last_name="Davis",
            date_of_birth="1960-11-30",
        )
        assert identity["verified"] is True

        # Patient mentions emergency symptoms during triage
        # This should immediately escalate regardless of prior progress
        triage_result = assess_symptom_urgency(
            chief_complaint="started having severe chest pain just now",
            symptoms=["sweating", "nausea"],
            severity="severe",
            duration="just started, 5 minutes ago",
        )
        assert triage_result["is_emergency"] is True
        assert triage_result["call_911"] is True


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_uninsured_patient_flow(self) -> None:
        """Test flow handles uninsured patients."""
        # Identity verification works the same
        identity = verify_patient_identity(
            first_name="David",
            last_name="Wilson",
            date_of_birth="1992-07-04",
        )
        assert identity["verified"] is True

        # Skip insurance, proceed to triage
        triage = assess_symptom_urgency(
            chief_complaint="annual checkup",
            severity="mild",
        )
        assert triage["acuity_level"] == "non_urgent"

        # Should still be able to schedule
        slots = get_available_slots(appointment_type="new_patient")
        assert slots["total_available"] > 0

    def test_infant_patient_flow(self) -> None:
        """Test flow for infant patients with age-based risk assessment."""
        # Verify identity (parent provides info)
        identity = verify_patient_identity(
            first_name="Baby",
            last_name="Miller",
            date_of_birth="2023-08-15",  # Less than 2 years old
        )
        assert identity["verified"] is True

        # Triage with age factor
        triage = assess_symptom_urgency(
            chief_complaint="fever and not eating",
            symptoms=["fussy", "warm to touch"],
            severity="moderate",
            age=1,  # 1 year old
        )
        # Infant with fever should be at least semi_urgent
        assert triage["acuity_level"] in ["semi_urgent", "urgent"]
        assert "age_risk_factor" in triage["red_flags"]

    def test_elderly_patient_flow(self) -> None:
        """Test flow for elderly patients with age-based risk assessment."""
        identity = verify_patient_identity(
            first_name="Eleanor",
            last_name="Thompson",
            date_of_birth="1940-02-28",
        )
        assert identity["verified"] is True

        triage = assess_symptom_urgency(
            chief_complaint="dizziness when standing",
            symptoms=["lightheaded", "occasional fall"],
            age=84,
        )
        # Elderly with dizziness/falls should have elevated urgency
        assert "age_risk_factor" in triage["red_flags"]

    def test_chronic_condition_flag(self) -> None:
        """Test that chronic conditions are appropriately flagged."""
        triage = assess_symptom_urgency(
            chief_complaint="ongoing knee pain",
            duration="3 months",
        )
        assert "chronic_condition" in triage["red_flags"]

    def test_multiple_symptoms_handling(self) -> None:
        """Test handling of multiple symptoms."""
        triage = assess_symptom_urgency(
            chief_complaint="not feeling well",
            symptoms=[
                "headache",
                "fatigue",
                "body aches",
                "sore throat",
                "mild cough",
            ],
            severity="moderate",
        )
        # Should assess based on overall picture
        assert triage["acuity_level"] in ["semi_urgent", "non_urgent"]
        assert len(triage["symptoms_assessed"]) == 5


class TestIntakeSessionModel:
    """Tests for IntakeSession model."""

    def test_create_new_session(self) -> None:
        """Test creating a new intake session."""
        session = IntakeSession(
            session_id="test_session_001",
            started_at=time.time(),
            updated_at=time.time(),
        )
        assert session.current_stage == "greeting"
        assert session.consent_obtained is False
        assert session.patient_identity is None

    def test_session_stage_progression(self) -> None:
        """Test session progresses through stages."""
        now = time.time()
        session = IntakeSession(
            session_id="test_session_002",
            started_at=now,
            updated_at=now,
        )

        # Progress through stages
        session.consent_obtained = True
        session.current_stage = "identity"

        session.patient_identity = PatientIdentity(
            first_name="Test",
            last_name="User",
            date_of_birth="1990-01-01",
            verified=True,
            patient_id="patient_123",
        )
        session.current_stage = "insurance"

        assert session.patient_identity.verified is True
        assert session.current_stage == "insurance"

    def test_session_serialization(self) -> None:
        """Test session can be serialized and deserialized."""
        now = time.time()
        session = IntakeSession(
            session_id="test_session_003",
            current_stage="triage",
            consent_obtained=True,
            patient_identity=PatientIdentity(
                first_name="Serialization",
                last_name="Test",
                date_of_birth="1985-06-15",
                verified=True,
            ),
            started_at=now,
            updated_at=now,
        )

        # Serialize to dict
        data = session.model_dump()
        assert data["session_id"] == "test_session_003"
        assert data["patient_identity"]["first_name"] == "Serialization"

        # Deserialize back
        restored = IntakeSession(**data)
        assert restored.session_id == session.session_id
        assert restored.patient_identity.first_name == "Serialization"


class TestRedisSessionPersistence:
    """Tests for Redis session persistence (uses fallback memory store)."""

    @pytest.fixture(autouse=True)
    def use_memory_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Use memory fallback for Redis operations."""
        monkeypatch.setenv("REDIS_FALLBACK", "1")

    def test_save_and_retrieve_session(self) -> None:
        """Test saving and retrieving intake session."""
        from ai_health_board.redis_store import get_intake_session, save_intake_session

        session = IntakeSession(
            session_id="persist_test_001",
            current_stage="demographics",
            consent_obtained=True,
            started_at=time.time(),
            updated_at=time.time(),
        )

        save_intake_session(session)
        retrieved = get_intake_session("persist_test_001")

        assert retrieved is not None
        assert retrieved.session_id == "persist_test_001"
        assert retrieved.current_stage == "demographics"

    def test_update_session(self) -> None:
        """Test updating an existing session."""
        from ai_health_board.redis_store import get_intake_session, save_intake_session

        session = IntakeSession(
            session_id="persist_test_002",
            current_stage="identity",
            started_at=time.time(),
            updated_at=time.time(),
        )
        save_intake_session(session)

        # Update session
        session.current_stage = "insurance"
        session.patient_identity = PatientIdentity(
            first_name="Update",
            last_name="Test",
            date_of_birth="1995-12-25",
            verified=True,
        )
        save_intake_session(session)

        retrieved = get_intake_session("persist_test_002")
        assert retrieved is not None
        assert retrieved.current_stage == "insurance"
        assert retrieved.patient_identity is not None
        assert retrieved.patient_identity.first_name == "Update"

    def test_list_sessions(self) -> None:
        """Test listing intake sessions."""
        from ai_health_board.redis_store import (
            list_intake_sessions,
            save_intake_session,
        )

        # Create multiple sessions
        for i in range(3):
            session = IntakeSession(
                session_id=f"list_test_{i}",
                current_stage="identity" if i % 2 == 0 else "triage",
                started_at=time.time(),
                updated_at=time.time() + i,
            )
            save_intake_session(session)

        # List all sessions
        all_sessions = list_intake_sessions()
        list_test_sessions = [s for s in all_sessions if s.session_id.startswith("list_test_")]
        assert len(list_test_sessions) >= 3

        # Filter by status
        identity_sessions = list_intake_sessions(status="identity")
        assert all(s.current_stage == "identity" for s in identity_sessions)

    def test_delete_session(self) -> None:
        """Test deleting an intake session."""
        from ai_health_board.redis_store import (
            delete_intake_session,
            get_intake_session,
            save_intake_session,
        )

        session = IntakeSession(
            session_id="delete_test_001",
            started_at=time.time(),
            updated_at=time.time(),
        )
        save_intake_session(session)

        # Verify saved
        assert get_intake_session("delete_test_001") is not None

        # Delete
        deleted = delete_intake_session("delete_test_001")
        assert deleted is True

        # Verify deleted
        assert get_intake_session("delete_test_001") is None

    def test_session_not_found(self) -> None:
        """Test getting non-existent session returns None."""
        from ai_health_board.redis_store import get_intake_session

        result = get_intake_session("nonexistent_session_xyz")
        assert result is None
