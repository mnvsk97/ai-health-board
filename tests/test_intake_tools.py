"""Unit tests for intake agent tools."""

from __future__ import annotations

import pytest

from ai_health_board.agents.tools import (
    EMERGENCY_KEYWORDS,
    assess_symptom_urgency,
    book_appointment,
    check_emergency_indicators,
    check_emergency_symptoms,
    get_available_slots,
    get_intake_session,
    get_triage_recommendation,
    lookup_carrier_by_name,
    lookup_patient_by_phone,
    save_demographics,
    save_intake_session,
    send_appointment_confirmation,
    validate_address,
    validate_phone_number,
    verify_insurance_eligibility,
    verify_patient_identity,
)


class TestEmergencyDetection:
    """Tests for emergency symptom detection."""

    @pytest.mark.parametrize(
        "symptom",
        [
            "chest pain",
            "chest pressure",
            "difficulty breathing",
            "can't breathe",
            "shortness of breath",
            "stroke",
            "face drooping",
            "arm weakness",
            "slurred speech",
            "severe bleeding",
            "unconscious",
            "passed out",
            "unresponsive",
            "seizure",
            "overdose",
            "anaphylaxis",
        ],
    )
    def test_detects_physical_emergencies(self, symptom: str) -> None:
        """Test that physical emergency symptoms are detected."""
        result = check_emergency_symptoms(symptom)
        assert result["is_emergency"] is True
        assert result["call_911"] is True
        assert result["acuity_level"] == "emergent"

    @pytest.mark.parametrize(
        "symptom",
        [
            "suicidal thoughts",
            "I want to die",
            "I want to kill myself",
        ],
    )
    def test_detects_mental_health_crisis(self, symptom: str) -> None:
        """Test that mental health crisis is detected with appropriate response."""
        result = check_emergency_symptoms(symptom)
        assert result["is_emergency"] is True
        assert result["emergency_type"] == "mental_health_crisis"
        assert result.get("call_988") is True
        # Mental health crisis should not recommend 911 by default
        assert result["call_911"] is False

    @pytest.mark.parametrize(
        "symptom",
        [
            "headache",
            "back pain",
            "feeling tired",
            "runny nose",
            "sore throat",
            "mild cough",
            "stomachache",
        ],
    )
    def test_non_emergency_symptoms(self, symptom: str) -> None:
        """Test that non-emergency symptoms are handled appropriately."""
        result = check_emergency_symptoms(symptom)
        assert result["is_emergency"] is False
        assert result["call_911"] is False

    def test_emergency_keywords_coverage(self) -> None:
        """Verify emergency keywords list covers basic conditions."""
        # Check some key conditions are covered (not comprehensive)
        basic_conditions = [
            "chest pain",
            "difficulty breathing",
            "stroke",
            "severe bleeding",
        ]
        for condition in basic_conditions:
            assert any(
                condition in keyword for keyword in EMERGENCY_KEYWORDS
            ), f"Missing condition: {condition}"


class TestCheckEmergencyIndicators:
    """Tests for the emergency indicator check."""

    def test_detects_infant_fever(self) -> None:
        """Test infant fever detection (only checks fever keyword)."""
        result = check_emergency_indicators(
            symptoms="baby has high fever",
            age=1,
        )
        assert result["is_emergency"] is True
        assert "infant_warning_signs" in result["indicators"]

    def test_detects_diabetic_confusion(self) -> None:
        """Test diabetes + confusion detection (requires exact match)."""
        result = check_emergency_indicators(
            symptoms="feeling confusion",
            medical_history=["diabetes"],  # Must be exact match
        )
        assert result["is_emergency"] is True
        assert "diabetic_emergency" in result["indicators"]

    def test_non_emergency_with_history(self) -> None:
        """Test that normal symptoms don't trigger emergency with history."""
        result = check_emergency_indicators(
            symptoms="headache and fatigue",
            age=35,
            medical_history=["high blood pressure"],
        )
        assert result["is_emergency"] is False


class TestAssessSymptomUrgency:
    """Tests for symptom urgency assessment."""

    def test_emergency_escalation(self) -> None:
        """Test that emergency symptoms trigger emergent acuity."""
        result = assess_symptom_urgency(
            chief_complaint="severe chest pain",
            symptoms=["chest tightness", "sweating"],
            severity="severe",
        )
        assert result["acuity_level"] == "emergent"
        assert result["is_emergency"] is True
        assert result["call_911"] is True

    def test_severe_non_emergency(self) -> None:
        """Test severe but non-emergency symptoms."""
        result = assess_symptom_urgency(
            chief_complaint="severe back pain",
            symptoms=["muscle spasm"],
            severity="severe",
        )
        assert result["acuity_level"] == "urgent"
        assert result["is_emergency"] is False

    def test_moderate_symptoms(self) -> None:
        """Test moderate symptom assessment."""
        result = assess_symptom_urgency(
            chief_complaint="persistent cough",
            symptoms=["congestion", "sore throat"],
            severity="moderate",
            duration="3 days",
        )
        assert result["acuity_level"] == "semi_urgent"

    def test_mild_symptoms(self) -> None:
        """Test mild symptom assessment."""
        result = assess_symptom_urgency(
            chief_complaint="mild headache",
            symptoms=["tired"],
            severity="mild",
            duration="1 week",
        )
        assert result["acuity_level"] == "non_urgent"

    def test_acute_onset_escalation(self) -> None:
        """Test that acute onset escalates acuity."""
        result = assess_symptom_urgency(
            chief_complaint="stomach pain",
            duration="sudden onset, just started",
        )
        # Acute onset should escalate to at least semi_urgent
        assert result["acuity_level"] in ["semi_urgent", "urgent"]
        assert "acute_onset" in result["red_flags"]

    def test_age_risk_factor(self) -> None:
        """Test that extreme ages are flagged as risk factors."""
        result = assess_symptom_urgency(
            chief_complaint="fever",
            age=85,  # Must be >70 to trigger
        )
        assert "age_risk_factor" in result["red_flags"]


class TestGetTriageRecommendation:
    """Tests for triage recommendation generation."""

    def test_emergency_recommendation(self) -> None:
        """Test emergency triage recommendation."""
        result = get_triage_recommendation(
            acuity_level="emergent",
            chief_complaint="chest pain",
            is_emergency=True,
        )
        assert result["action"] == "immediate_escalation"
        assert "911" in result["message"]
        assert result["appointment_needed"] is False

    def test_urgent_recommendation(self) -> None:
        """Test urgent triage recommendation."""
        result = get_triage_recommendation(
            acuity_level="urgent",
            chief_complaint="severe back pain",
        )
        assert result["action"] == "same_day_appointment"
        assert result["appointment_needed"] is True
        assert result["appointment_urgency"] == "same_day"

    def test_semi_urgent_recommendation(self) -> None:
        """Test semi-urgent triage recommendation."""
        result = get_triage_recommendation(
            acuity_level="semi_urgent",
            chief_complaint="persistent cough",
        )
        assert result["action"] == "priority_appointment"
        assert result["appointment_urgency"] == "within_48_hours"

    def test_non_urgent_recommendation(self) -> None:
        """Test non-urgent triage recommendation."""
        result = get_triage_recommendation(
            acuity_level="non_urgent",
            chief_complaint="annual checkup",
        )
        assert result["action"] == "routine_appointment"
        assert result["appointment_urgency"] == "routine"


class TestIdentityVerification:
    """Tests for patient identity verification."""

    def test_verify_patient_identity(self) -> None:
        """Test basic identity verification."""
        result = verify_patient_identity(
            first_name="John",
            last_name="Doe",
            date_of_birth="1980-05-15",
        )
        assert result["verified"] is True
        assert "patient_id" in result
        assert result["match_confidence"] >= 0.8

    def test_verify_with_ssn_increases_confidence(self) -> None:
        """Test that SSN increases match confidence."""
        without_ssn = verify_patient_identity(
            first_name="Jane",
            last_name="Smith",
            date_of_birth="1990-03-20",
        )
        with_ssn = verify_patient_identity(
            first_name="Jane",
            last_name="Smith",
            date_of_birth="1990-03-20",
            ssn_last_four="1234",
        )
        assert with_ssn["match_confidence"] > without_ssn["match_confidence"]

    def test_lookup_patient_by_phone(self) -> None:
        """Test phone-based patient lookup."""
        result = lookup_patient_by_phone("555-123-4567")
        assert result["found"] is True
        assert "patient_id" in result

    def test_invalid_phone_number(self) -> None:
        """Test handling of invalid phone numbers."""
        result = lookup_patient_by_phone("123")  # Too short
        assert result["found"] is False
        assert "error" in result


class TestInsuranceVerification:
    """Tests for insurance verification."""

    def test_verify_insurance_eligibility(self) -> None:
        """Test insurance eligibility verification."""
        result = verify_insurance_eligibility(
            carrier_name="Blue Cross",
            member_id="ABC123456",
            group_number="GRP001",
        )
        assert result["eligible"] is True
        assert "copay_primary_care" in result
        assert result["in_network"] is True

    def test_lookup_carrier_by_name(self) -> None:
        """Test carrier lookup by name."""
        result = lookup_carrier_by_name("blue cross")
        assert result["found"] is True
        assert len(result["carriers"]) > 0
        assert result["carriers"][0]["carrier_id"] == "BCBS"

    def test_lookup_carrier_not_found(self) -> None:
        """Test carrier lookup for unknown carrier."""
        result = lookup_carrier_by_name("Unknown Insurance Co")
        assert result["found"] is False


class TestDemographicsValidation:
    """Tests for demographics validation."""

    def test_validate_valid_address(self) -> None:
        """Test address validation with valid data."""
        result = validate_address(
            street="123 Main St",
            city="New York",
            state="NY",
            zip_code="10001",
        )
        assert result["valid"] is True
        assert result["standardized_address"]["state"] == "NY"

    def test_validate_invalid_state(self) -> None:
        """Test address validation with invalid state."""
        result = validate_address(
            street="123 Main St",
            city="Somewhere",
            state="XX",  # Invalid
            zip_code="12345",
        )
        assert result["valid"] is False
        assert "error" in result

    def test_validate_invalid_zip(self) -> None:
        """Test address validation with invalid ZIP code."""
        result = validate_address(
            street="123 Main St",
            city="Chicago",
            state="IL",
            zip_code="123",  # Too short
        )
        assert result["valid"] is False

    def test_validate_phone_number(self) -> None:
        """Test phone number validation."""
        result = validate_phone_number("555-123-4567")
        assert result["valid"] is True
        assert result["formatted_phone"] == "(555) 123-4567"

    def test_validate_phone_with_country_code(self) -> None:
        """Test phone validation strips country code."""
        result = validate_phone_number("+1 555 123 4567")
        assert result["valid"] is True
        assert result["digits"] == "5551234567"

    def test_validate_invalid_phone(self) -> None:
        """Test phone validation with invalid number."""
        result = validate_phone_number("123-456")  # Too short
        assert result["valid"] is False

    def test_save_demographics(self) -> None:
        """Test saving demographics."""
        result = save_demographics(
            session_id="test_session_123",
            street_address="123 Main St",
            city="New York",
            state="NY",
            zip_code="10001",
            phone_number="555-123-4567",
            email="test@example.com",
            emergency_contact_name="Jane Doe",
            emergency_contact_phone="555-987-6543",
            emergency_contact_relationship="spouse",
        )
        assert result["saved"] is True
        assert result["session_id"] == "test_session_123"


class TestAppointmentScheduling:
    """Tests for appointment scheduling."""

    def test_get_available_slots(self) -> None:
        """Test retrieving available slots."""
        result = get_available_slots(
            specialty="family_medicine",
            appointment_type="new_patient",
        )
        assert "slots" in result
        assert result["total_available"] > 0
        assert all(slot["available"] for slot in result["slots"])

    def test_book_appointment(self) -> None:
        """Test booking an appointment."""
        result = book_appointment(
            slot_id="slot_12345",
            patient_id="patient_67890",
            reason="Annual checkup",
        )
        assert result["success"] is True
        assert "appointment_id" in result
        assert "confirmation_number" in result
        assert len(result["instructions"]) > 0

    def test_send_appointment_confirmation(self) -> None:
        """Test sending appointment confirmation."""
        result = send_appointment_confirmation(
            appointment_id="appt_123",
            patient_id="patient_456",
            method="email",
            email="patient@example.com",
        )
        assert result["sent"] is True
        assert result["method"] == "email"


class TestSessionManagement:
    """Tests for intake session management."""

    def test_save_intake_session(self) -> None:
        """Test saving intake session state."""
        result = save_intake_session(
            session_id="session_abc",
            current_stage="identity",
            data={"first_name": "John", "last_name": "Doe"},
        )
        assert result["saved"] is True
        assert result["current_stage"] == "identity"

    def test_get_intake_session_not_found(self) -> None:
        """Test getting a non-existent session."""
        result = get_intake_session("nonexistent_session")
        assert result["found"] is False
        assert result["current_stage"] == "greeting"  # Default stage


class TestToolSchemas:
    """Tests for tool schema definitions."""

    def test_all_tools_have_schemas(self) -> None:
        """Verify all registered tools have corresponding schemas."""
        from ai_health_board.agents.tools import TOOL_REGISTRY, tool_schemas

        schemas = tool_schemas()
        schema_names = {s["function"]["name"] for s in schemas}

        for tool_name in TOOL_REGISTRY:
            assert tool_name in schema_names, f"Missing schema for tool: {tool_name}"

    def test_schemas_are_valid_openai_format(self) -> None:
        """Verify schemas follow OpenAI function calling format."""
        from ai_health_board.agents.tools import tool_schemas

        for schema in tool_schemas():
            assert schema["type"] == "function"
            assert "function" in schema
            func = schema["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            assert func["parameters"]["type"] == "object"
