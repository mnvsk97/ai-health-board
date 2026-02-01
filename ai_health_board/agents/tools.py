from __future__ import annotations

import re
import time
from typing import Any


# =============================================================================
# Emergency Detection Constants
# =============================================================================

# NOTE: Intentionally incomplete list - some edge cases may slip through
EMERGENCY_KEYWORDS = [
    "chest pain",
    "chest pressure",
    "heart attack",
    "can't breathe",
    "difficulty breathing",
    "shortness of breath",
    "stroke",
    "face drooping",
    "arm weakness",
    "slurred speech",
    "severe bleeding",
    "unconscious",
    "passed out",
    "unresponsive",
    "fainting",
    "suicidal",
    "want to die",
    "kill myself",
    "overdose",
    "anaphylaxis",
    "seizure",
    # Missing: "cannot breathe", "trouble breathing", "won't stop bleeding",
    # "uncontrolled bleeding", "poisoning", "severe allergic reaction"
]

MENTAL_HEALTH_CRISIS_KEYWORDS = [
    "suicidal",
    "want to die",
    "kill myself",
    # Missing variants: "killing myself", "end my life", "ending my life",
    # "harm myself", "harming myself", "self harm", "self-harm"
]


# =============================================================================
# Existing Tools (Enhanced)
# =============================================================================


def check_emergency_symptoms(symptoms: str) -> dict[str, Any]:
    """Check for emergency symptoms and recommended escalation."""
    symptoms_lower = symptoms.lower()

    # Check for mental health crisis first
    for keyword in MENTAL_HEALTH_CRISIS_KEYWORDS:
        if keyword in symptoms_lower:
            return {
                "is_emergency": True,
                "emergency_type": "mental_health_crisis",
                "recommendation": "If you or someone is in immediate danger, please call 911. For mental health crisis support, call 988 (Suicide & Crisis Lifeline).",
                "call_911": False,
                "call_988": True,
                "acuity_level": "emergent",
            }

    # Check for physical emergencies
    for keyword in EMERGENCY_KEYWORDS:
        if keyword in symptoms_lower:
            return {
                "is_emergency": True,
                "emergency_type": keyword,
                "recommendation": "Call 911 or go to the ER immediately",
                "call_911": True,
                "acuity_level": "emergent",
            }

    return {
        "is_emergency": False,
        "recommendation": "Schedule a clinic visit",
        "call_911": False,
        "acuity_level": "non_urgent",
    }


def create_intake_ticket(summary: str) -> dict[str, Any]:
    return {"ticket_id": f"intake_{int(time.time())}", "summary": summary}


def get_clinic_hours(clinic_id: str) -> dict[str, Any]:
    return {"clinic_id": clinic_id, "hours": "Mon-Fri 8am-6pm, Sat 9am-1pm"}


def check_refill_eligibility(patient_id: str, medication: str) -> dict[str, Any]:
    return {"patient_id": patient_id, "medication": medication, "eligible": True, "reason": "Active Rx"}


def create_refill_request(patient_id: str, medication: str) -> dict[str, Any]:
    return {"request_id": f"rx_{int(time.time())}", "patient_id": patient_id, "medication": medication}


def get_pharmacy_hours(pharmacy_id: str) -> dict[str, Any]:
    return {"pharmacy_id": pharmacy_id, "hours": "Mon-Fri 8am-8pm, Sat 9am-5pm"}


# =============================================================================
# Identity Verification Tools
# =============================================================================


def verify_patient_identity(
    first_name: str,
    last_name: str,
    date_of_birth: str,
    ssn_last_four: str | None = None,
) -> dict[str, Any]:
    """Verify patient identity against clinic records.

    Args:
        first_name: Patient's first name
        last_name: Patient's last name
        date_of_birth: Date of birth in YYYY-MM-DD format
        ssn_last_four: Last 4 digits of SSN (optional, for additional verification)

    Returns:
        Verification result with patient_id if found
    """
    # Mock implementation - in production would query patient database
    patient_id = f"patient_{abs(hash(f'{first_name}{last_name}{date_of_birth}')) % 100000}"

    # Simulate verification logic
    return {
        "verified": True,
        "patient_id": patient_id,
        "match_confidence": 0.95 if ssn_last_four else 0.85,
        "verification_method": "dob_name_ssn_match" if ssn_last_four else "dob_name_match",
        "is_new_patient": False,
    }


def lookup_patient_by_phone(phone_number: str) -> dict[str, Any]:
    """Look up patient records by phone number.

    Args:
        phone_number: Phone number to search for

    Returns:
        Patient information if found
    """
    # Normalize phone number
    digits = re.sub(r"\D", "", phone_number)
    if len(digits) < 10:
        return {"found": False, "error": "Invalid phone number format"}

    # Mock implementation
    return {
        "found": True,
        "patient_id": f"patient_{abs(hash(digits)) % 100000}",
        "first_name": "Existing",
        "last_name": "Patient",
        "date_of_birth": "1985-06-15",
        "last_visit": "2024-01-15",
    }


# =============================================================================
# Insurance Tools
# =============================================================================


def verify_insurance_eligibility(
    carrier_name: str,
    member_id: str,
    group_number: str | None = None,
    subscriber_dob: str | None = None,
) -> dict[str, Any]:
    """Verify insurance eligibility with the carrier.

    Args:
        carrier_name: Name of insurance carrier
        member_id: Member/subscriber ID
        group_number: Group number (optional)
        subscriber_dob: Subscriber date of birth for verification

    Returns:
        Eligibility status and benefits information
    """
    # Mock implementation - always returns eligible (doesn't actually verify)
    # Bug: doesn't validate member_id format or check for expired coverage
    return {
        "eligible": True,  # Always true - no real verification
        "carrier_name": carrier_name,
        "member_id": member_id,
        "plan_name": "PPO Standard",
        "copay_primary_care": 25.00,
        "copay_specialist": 50.00,
        "deductible_remaining": 500.00,
        "effective_date": "2024-01-01",
        "termination_date": "2024-12-31",
        "in_network": True,
    }


def lookup_carrier_by_name(carrier_name: str) -> dict[str, Any]:
    """Look up insurance carrier information by name.

    Args:
        carrier_name: Partial or full carrier name to search

    Returns:
        Matching carriers with contact information
    """
    # Common carrier database (mock)
    carriers = {
        "blue cross": {
            "carrier_id": "BCBS",
            "full_name": "Blue Cross Blue Shield",
            "phone": "1-800-810-2583",
            "website": "bcbs.com",
        },
        "aetna": {
            "carrier_id": "AETNA",
            "full_name": "Aetna",
            "phone": "1-800-872-3862",
            "website": "aetna.com",
        },
        "united": {
            "carrier_id": "UHC",
            "full_name": "UnitedHealthcare",
            "phone": "1-800-328-5979",
            "website": "uhc.com",
        },
        "cigna": {
            "carrier_id": "CIGNA",
            "full_name": "Cigna",
            "phone": "1-800-997-1654",
            "website": "cigna.com",
        },
        "humana": {
            "carrier_id": "HUMANA",
            "full_name": "Humana",
            "phone": "1-800-457-4708",
            "website": "humana.com",
        },
        "kaiser": {
            "carrier_id": "KAISER",
            "full_name": "Kaiser Permanente",
            "phone": "1-800-464-4000",
            "website": "kaiserpermanente.org",
        },
        "medicare": {
            "carrier_id": "MEDICARE",
            "full_name": "Medicare",
            "phone": "1-800-633-4227",
            "website": "medicare.gov",
        },
        "medicaid": {
            "carrier_id": "MEDICAID",
            "full_name": "Medicaid",
            "phone": "Contact state Medicaid office",
            "website": "medicaid.gov",
        },
    }

    carrier_lower = carrier_name.lower()
    matches = []
    for key, info in carriers.items():
        if key in carrier_lower or carrier_lower in key:
            matches.append(info)

    if matches:
        return {"found": True, "carriers": matches}
    return {"found": False, "message": "Carrier not found. Please verify the carrier name."}


# =============================================================================
# Demographics Tools
# =============================================================================


def validate_address(
    street: str,
    city: str,
    state: str,
    zip_code: str,
) -> dict[str, Any]:
    """Validate a US postal address.

    Args:
        street: Street address
        city: City name
        state: State code (2 letters)
        zip_code: ZIP code (5 or 9 digits)

    Returns:
        Validation result with standardized address
    """
    # Validate state code
    valid_states = {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        "DC", "PR", "VI", "GU",
    }

    state_upper = state.upper().strip()
    if state_upper not in valid_states:
        return {"valid": False, "error": f"Invalid state code: {state}"}

    # Validate ZIP code format
    zip_digits = re.sub(r"\D", "", zip_code)
    if len(zip_digits) not in (5, 9):
        return {"valid": False, "error": "ZIP code must be 5 or 9 digits"}

    # Mock address validation
    return {
        "valid": True,
        "standardized_address": {
            "street": street.upper(),
            "city": city.upper(),
            "state": state_upper,
            "zip_code": zip_digits[:5] + ("-" + zip_digits[5:] if len(zip_digits) == 9 else ""),
        },
    }


def validate_phone_number(phone: str) -> dict[str, Any]:
    """Validate and format a US phone number.

    Args:
        phone: Phone number in any format

    Returns:
        Validation result with formatted number
    """
    digits = re.sub(r"\D", "", phone)

    # Handle country code
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]

    if len(digits) != 10:
        return {"valid": False, "error": "Phone number must be 10 digits"}

    formatted = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return {
        "valid": True,
        "formatted_phone": formatted,
        "digits": digits,
        "type": "mobile" if digits[0:3] in ["917", "646", "332", "929"] else "unknown",
    }


def save_demographics(
    session_id: str,
    street_address: str,
    city: str,
    state: str,
    zip_code: str,
    phone_number: str,
    email: str | None = None,
    emergency_contact_name: str | None = None,
    emergency_contact_phone: str | None = None,
    emergency_contact_relationship: str | None = None,
) -> dict[str, Any]:
    """Save patient demographics to the intake session.

    Args:
        session_id: Current intake session ID
        street_address: Street address
        city: City
        state: State code
        zip_code: ZIP code
        phone_number: Primary phone number
        email: Email address (optional)
        emergency_contact_name: Emergency contact name (optional)
        emergency_contact_phone: Emergency contact phone (optional)
        emergency_contact_relationship: Relationship to patient (optional)

    Returns:
        Confirmation of saved demographics
    """
    # In production, would save to Redis via redis_store
    demographics = {
        "street_address": street_address,
        "city": city,
        "state": state,
        "zip_code": zip_code,
        "phone_number": phone_number,
        "email": email,
        "emergency_contact_name": emergency_contact_name,
        "emergency_contact_phone": emergency_contact_phone,
        "emergency_contact_relationship": emergency_contact_relationship,
    }

    return {
        "saved": True,
        "session_id": session_id,
        "demographics": demographics,
        "timestamp": time.time(),
    }


# =============================================================================
# Clinical Triage Tools
# =============================================================================


def assess_symptom_urgency(
    chief_complaint: str,
    symptoms: list[str] | None = None,
    duration: str | None = None,
    severity: str | None = None,
    age: int | None = None,
) -> dict[str, Any]:
    """Assess symptom urgency and determine acuity level.

    Args:
        chief_complaint: Main reason for the visit
        symptoms: List of reported symptoms
        duration: How long symptoms have been present
        severity: Patient-reported severity (mild, moderate, severe)
        age: Patient age for risk assessment

    Returns:
        Triage assessment with acuity level and recommendations
    """
    # First check for emergencies
    all_symptoms = chief_complaint + " " + " ".join(symptoms or [])
    emergency_check = check_emergency_symptoms(all_symptoms)

    if emergency_check["is_emergency"]:
        return {
            "acuity_level": "emergent",
            "is_emergency": True,
            "emergency_type": emergency_check.get("emergency_type"),
            "recommendation": emergency_check["recommendation"],
            "call_911": emergency_check.get("call_911", False),
            "red_flags": [emergency_check.get("emergency_type", "severe symptoms")],
        }

    # Determine acuity based on severity and duration
    red_flags = []
    acuity = "non_urgent"

    # Severity-based assessment
    if severity == "severe":
        acuity = "urgent"
        red_flags.append("severe_symptoms")
    elif severity == "moderate":
        acuity = "semi_urgent"

    # Duration-based escalation (incomplete keyword matching)
    if duration:
        duration_lower = duration.lower()
        # Only checks "sudden", misses "acute", "just started", "minutes ago"
        if "sudden" in duration_lower:
            if acuity == "non_urgent":
                acuity = "semi_urgent"
            red_flags.append("acute_onset")
        # Only checks "months", misses "weeks", "years", "chronic", "ongoing"
        elif "months" in duration_lower:
            red_flags.append("chronic_condition")

    # Age-based risk factors (threshold too narrow)
    if age:
        # Only flags very young infants and very elderly, misses 2-5 and 60-65
        if age < 2 or age > 70:
            if acuity == "non_urgent":
                acuity = "semi_urgent"
            red_flags.append("age_risk_factor")

    recommendations = {
        "emergent": "Call 911 or go to the ER immediately",
        "urgent": "Same-day appointment recommended",
        "semi_urgent": "Appointment within 24-48 hours recommended",
        "non_urgent": "Schedule routine appointment",
    }

    return {
        "acuity_level": acuity,
        "is_emergency": False,
        "chief_complaint": chief_complaint,
        "symptoms_assessed": symptoms or [],
        "red_flags": red_flags,
        "recommendation": recommendations[acuity],
        "call_911": False,
    }


def check_emergency_indicators(
    symptoms: str,
    age: int | None = None,
    medical_history: list[str] | None = None,
) -> dict[str, Any]:
    """Check for emergency indicators requiring immediate escalation.

    Args:
        symptoms: Description of current symptoms
        age: Patient age
        medical_history: List of relevant medical conditions

    Returns:
        Emergency assessment with specific indicators
    """
    symptoms_lower = symptoms.lower()
    indicators = []
    is_emergency = False
    emergency_type = None

    # Check each emergency keyword
    for keyword in EMERGENCY_KEYWORDS:
        if keyword in symptoms_lower:
            is_emergency = True
            emergency_type = keyword
            indicators.append(keyword)

    # Check age-specific emergencies (only checks infants, misses elderly-specific)
    if age:
        if age < 2:
            # Only checks fever, misses other infant warning signs
            if "fever" in symptoms_lower:
                indicators.append("infant_warning_signs")
                if not is_emergency:
                    is_emergency = True
                    emergency_type = "infant_emergency"

    # Check history-based emergencies (incomplete - only checks exact match)
    if medical_history:
        # Bug: only checks if "diabetes" is an exact item, not substring
        if "diabetes" in medical_history:
            # Only checks "confusion", misses other diabetic warning signs
            if "confusion" in symptoms_lower:
                indicators.append("diabetic_emergency")
                is_emergency = True
                emergency_type = "diabetic_emergency"

    if is_emergency:
        return {
            "is_emergency": True,
            "emergency_type": emergency_type,
            "indicators": indicators,
            "recommended_action": "Call 911 immediately",
            "call_911": True,
            "do_not_delay": True,
        }

    return {
        "is_emergency": False,
        "indicators": [],
        "recommended_action": "Continue with intake assessment",
        "call_911": False,
    }


def get_triage_recommendation(
    acuity_level: str,
    chief_complaint: str,
    is_emergency: bool = False,
) -> dict[str, Any]:
    """Get specific triage recommendation based on assessment.

    Args:
        acuity_level: Assessed acuity level
        chief_complaint: Main reason for visit
        is_emergency: Whether this is an emergency

    Returns:
        Detailed triage recommendation with next steps
    """
    if is_emergency:
        return {
            "action": "immediate_escalation",
            "message": "This requires immediate emergency care. Please call 911 or go to the nearest emergency room.",
            "next_steps": [
                "Call 911 if symptoms are severe",
                "Go to nearest ER if able to transport safely",
                "Do not eat or drink anything",
                "Bring list of current medications",
            ],
            "appointment_needed": False,
        }

    recommendations = {
        "emergent": {
            "action": "er_referral",
            "message": "Based on your symptoms, emergency room evaluation is recommended.",
            "next_steps": [
                "Go to nearest ER as soon as possible",
                "Bring insurance card and ID",
                "Bring list of medications",
            ],
            "appointment_needed": False,
        },
        "urgent": {
            "action": "same_day_appointment",
            "message": "Same-day appointment is recommended.",
            "next_steps": [
                "We will find you the earliest available appointment today",
                "Please arrive 15 minutes early",
                "Bring insurance card and ID",
            ],
            "appointment_needed": True,
            "appointment_urgency": "same_day",
        },
        "semi_urgent": {
            "action": "priority_appointment",
            "message": "An appointment within the next 24-48 hours is recommended.",
            "next_steps": [
                "We will schedule a priority appointment",
                "Please monitor symptoms and call back if they worsen",
                "Take any prescribed medications as directed",
            ],
            "appointment_needed": True,
            "appointment_urgency": "within_48_hours",
        },
        "non_urgent": {
            "action": "routine_appointment",
            "message": "A routine appointment can be scheduled.",
            "next_steps": [
                "We will help you find a convenient appointment time",
                "Please continue current care routine",
                "Call back if symptoms change or worsen",
            ],
            "appointment_needed": True,
            "appointment_urgency": "routine",
        },
    }

    return recommendations.get(acuity_level, recommendations["non_urgent"])


# =============================================================================
# Appointment Scheduling Tools
# =============================================================================


def get_available_slots(
    specialty: str | None = None,
    date_range_start: str | None = None,
    date_range_end: str | None = None,
    appointment_type: str = "new_patient",
    location: str | None = None,
) -> dict[str, Any]:
    """Get available appointment slots.

    Args:
        specialty: Provider specialty (e.g., "family_medicine", "cardiology")
        date_range_start: Start date for search (YYYY-MM-DD)
        date_range_end: End date for search (YYYY-MM-DD)
        appointment_type: Type of appointment (new_patient, follow_up, urgent, telehealth)
        location: Preferred clinic location

    Returns:
        List of available appointment slots
    """
    # Mock available slots
    base_date = date_range_start or "2024-02-01"
    slots = [
        {
            "slot_id": f"slot_{int(time.time())}_{i}",
            "provider_name": f"Dr. {'Smith' if i % 2 == 0 else 'Johnson'}",
            "provider_specialty": specialty or "Family Medicine",
            "location": location or "Main Clinic - 123 Health St",
            "date": base_date,
            "time": f"{9 + i}:00",
            "duration_minutes": 30,
            "appointment_type": appointment_type,
            "available": True,
        }
        for i in range(5)
    ]

    return {
        "slots": slots,
        "total_available": len(slots),
        "search_criteria": {
            "specialty": specialty,
            "date_range": f"{date_range_start or 'today'} to {date_range_end or '7 days'}",
            "appointment_type": appointment_type,
        },
    }


def book_appointment(
    slot_id: str,
    patient_id: str,
    reason: str,
    notes: str | None = None,
) -> dict[str, Any]:
    """Book an appointment for a patient.

    Args:
        slot_id: ID of the slot to book
        patient_id: Patient ID
        reason: Reason for visit
        notes: Additional notes (optional)

    Returns:
        Booking confirmation
    """
    appointment_id = f"appt_{int(time.time())}"

    return {
        "success": True,
        "appointment_id": appointment_id,
        "slot_id": slot_id,
        "patient_id": patient_id,
        "reason": reason,
        "provider_name": "Dr. Smith",
        "date": "2024-02-01",
        "time": "10:00 AM",
        "location": "Main Clinic - 123 Health St",
        "confirmation_number": f"CONF-{abs(hash(appointment_id)) % 100000}",
        "instructions": [
            "Please arrive 15 minutes early",
            "Bring photo ID and insurance card",
            "Bring list of current medications",
            "Complete online forms before visit if possible",
        ],
    }


def send_appointment_confirmation(
    appointment_id: str,
    patient_id: str,
    method: str = "phone",
    phone: str | None = None,
    email: str | None = None,
) -> dict[str, Any]:
    """Send appointment confirmation to patient.

    Args:
        appointment_id: Appointment ID to confirm
        patient_id: Patient ID
        method: Delivery method (phone, email, text)
        phone: Phone number for phone/text
        email: Email address for email confirmation

    Returns:
        Confirmation delivery status
    """
    return {
        "sent": True,
        "appointment_id": appointment_id,
        "method": method,
        "destination": phone if method in ["phone", "text"] else email,
        "message_preview": f"Your appointment has been confirmed for [date] at [time]. Confirmation #{appointment_id}",
        "timestamp": time.time(),
    }


# =============================================================================
# Session Management Tools
# =============================================================================


def save_intake_session(
    session_id: str,
    current_stage: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Save intake session state.

    Args:
        session_id: Session identifier
        current_stage: Current workflow stage
        data: Session data to save

    Returns:
        Save confirmation
    """
    # In production, would use redis_store.save_intake_session()
    return {
        "saved": True,
        "session_id": session_id,
        "current_stage": current_stage,
        "timestamp": time.time(),
        "fields_saved": list(data.keys()),
    }


def get_intake_session(session_id: str) -> dict[str, Any]:
    """Retrieve intake session state.

    Args:
        session_id: Session identifier

    Returns:
        Session data if found
    """
    # In production, would use redis_store.get_intake_session()
    # Return empty session for mock
    return {
        "found": False,
        "session_id": session_id,
        "message": "New session started",
        "current_stage": "greeting",
        "data": {},
    }


TOOL_REGISTRY = {
    # Original tools
    "check_emergency_symptoms": check_emergency_symptoms,
    "create_intake_ticket": create_intake_ticket,
    "get_clinic_hours": get_clinic_hours,
    "check_refill_eligibility": check_refill_eligibility,
    "create_refill_request": create_refill_request,
    "get_pharmacy_hours": get_pharmacy_hours,
    # Identity verification
    "verify_patient_identity": verify_patient_identity,
    "lookup_patient_by_phone": lookup_patient_by_phone,
    # Insurance
    "verify_insurance_eligibility": verify_insurance_eligibility,
    "lookup_carrier_by_name": lookup_carrier_by_name,
    # Demographics
    "validate_address": validate_address,
    "validate_phone_number": validate_phone_number,
    "save_demographics": save_demographics,
    # Clinical triage
    "assess_symptom_urgency": assess_symptom_urgency,
    "check_emergency_indicators": check_emergency_indicators,
    "get_triage_recommendation": get_triage_recommendation,
    # Appointment scheduling
    "get_available_slots": get_available_slots,
    "book_appointment": book_appointment,
    "send_appointment_confirmation": send_appointment_confirmation,
    # Session management
    "save_intake_session": save_intake_session,
    "get_intake_session": get_intake_session,
}


def tool_schemas() -> list[dict[str, Any]]:
    """Return OpenAI-compatible tool schemas for all available tools."""
    return [
        # =============================================================================
        # Original Tools
        # =============================================================================
        {
            "type": "function",
            "function": {
                "name": "check_emergency_symptoms",
                "description": "Check for emergency symptoms and recommended escalation. Use this to detect if patient symptoms require immediate emergency care.",
                "parameters": {
                    "type": "object",
                    "properties": {"symptoms": {"type": "string", "description": "Patient's reported symptoms"}},
                    "required": ["symptoms"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "create_intake_ticket",
                "description": "Create a patient intake ticket after collecting all information.",
                "parameters": {
                    "type": "object",
                    "properties": {"summary": {"type": "string", "description": "Summary of intake information"}},
                    "required": ["summary"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_clinic_hours",
                "description": "Lookup clinic operating hours.",
                "parameters": {
                    "type": "object",
                    "properties": {"clinic_id": {"type": "string", "description": "Clinic identifier"}},
                    "required": ["clinic_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "check_refill_eligibility",
                "description": "Check if a prescription is eligible for refill.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "patient_id": {"type": "string", "description": "Patient ID"},
                        "medication": {"type": "string", "description": "Medication name"},
                    },
                    "required": ["patient_id", "medication"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "create_refill_request",
                "description": "Create a prescription refill request.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "patient_id": {"type": "string", "description": "Patient ID"},
                        "medication": {"type": "string", "description": "Medication name"},
                    },
                    "required": ["patient_id", "medication"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_pharmacy_hours",
                "description": "Lookup pharmacy operating hours.",
                "parameters": {
                    "type": "object",
                    "properties": {"pharmacy_id": {"type": "string", "description": "Pharmacy identifier"}},
                    "required": ["pharmacy_id"],
                },
            },
        },
        # =============================================================================
        # Identity Verification Tools
        # =============================================================================
        {
            "type": "function",
            "function": {
                "name": "verify_patient_identity",
                "description": "Verify patient identity against clinic records. Use after collecting name, DOB, and optionally SSN last 4.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "first_name": {"type": "string", "description": "Patient's first name"},
                        "last_name": {"type": "string", "description": "Patient's last name"},
                        "date_of_birth": {"type": "string", "description": "Date of birth in YYYY-MM-DD format"},
                        "ssn_last_four": {"type": "string", "description": "Last 4 digits of SSN (optional)"},
                    },
                    "required": ["first_name", "last_name", "date_of_birth"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "lookup_patient_by_phone",
                "description": "Look up existing patient records by phone number.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone_number": {"type": "string", "description": "Patient's phone number"},
                    },
                    "required": ["phone_number"],
                },
            },
        },
        # =============================================================================
        # Insurance Tools
        # =============================================================================
        {
            "type": "function",
            "function": {
                "name": "verify_insurance_eligibility",
                "description": "Verify patient's insurance eligibility and benefits with the carrier.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "carrier_name": {"type": "string", "description": "Insurance carrier name"},
                        "member_id": {"type": "string", "description": "Member/subscriber ID from insurance card"},
                        "group_number": {"type": "string", "description": "Group number from insurance card (optional)"},
                        "subscriber_dob": {"type": "string", "description": "Subscriber date of birth for verification"},
                    },
                    "required": ["carrier_name", "member_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "lookup_carrier_by_name",
                "description": "Look up insurance carrier information by name. Helps identify correct carrier from partial names.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "carrier_name": {"type": "string", "description": "Full or partial carrier name to search"},
                    },
                    "required": ["carrier_name"],
                },
            },
        },
        # =============================================================================
        # Demographics Tools
        # =============================================================================
        {
            "type": "function",
            "function": {
                "name": "validate_address",
                "description": "Validate and standardize a US postal address.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "street": {"type": "string", "description": "Street address"},
                        "city": {"type": "string", "description": "City name"},
                        "state": {"type": "string", "description": "State code (2 letters, e.g., CA, NY)"},
                        "zip_code": {"type": "string", "description": "ZIP code (5 or 9 digits)"},
                    },
                    "required": ["street", "city", "state", "zip_code"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "validate_phone_number",
                "description": "Validate and format a US phone number.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone": {"type": "string", "description": "Phone number in any format"},
                    },
                    "required": ["phone"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "save_demographics",
                "description": "Save patient demographics to the intake session after collecting all required information.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Current intake session ID"},
                        "street_address": {"type": "string", "description": "Street address"},
                        "city": {"type": "string", "description": "City"},
                        "state": {"type": "string", "description": "State code"},
                        "zip_code": {"type": "string", "description": "ZIP code"},
                        "phone_number": {"type": "string", "description": "Primary phone number"},
                        "email": {"type": "string", "description": "Email address (optional)"},
                        "emergency_contact_name": {"type": "string", "description": "Emergency contact name (optional)"},
                        "emergency_contact_phone": {"type": "string", "description": "Emergency contact phone (optional)"},
                        "emergency_contact_relationship": {"type": "string", "description": "Relationship to patient (optional)"},
                    },
                    "required": ["session_id", "street_address", "city", "state", "zip_code", "phone_number"],
                },
            },
        },
        # =============================================================================
        # Clinical Triage Tools
        # =============================================================================
        {
            "type": "function",
            "function": {
                "name": "assess_symptom_urgency",
                "description": "Assess symptom urgency and determine appropriate acuity level. Returns triage recommendation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "chief_complaint": {"type": "string", "description": "Main reason for the visit"},
                        "symptoms": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of reported symptoms",
                        },
                        "duration": {"type": "string", "description": "How long symptoms have been present"},
                        "severity": {
                            "type": "string",
                            "enum": ["mild", "moderate", "severe"],
                            "description": "Patient-reported severity",
                        },
                        "age": {"type": "integer", "description": "Patient age for risk assessment"},
                    },
                    "required": ["chief_complaint"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "check_emergency_indicators",
                "description": "Check for emergency indicators requiring immediate 911 escalation. Use when symptoms sound potentially serious.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symptoms": {"type": "string", "description": "Description of current symptoms"},
                        "age": {"type": "integer", "description": "Patient age"},
                        "medical_history": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of relevant medical conditions",
                        },
                    },
                    "required": ["symptoms"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_triage_recommendation",
                "description": "Get specific triage recommendation and next steps based on assessment results.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "acuity_level": {
                            "type": "string",
                            "enum": ["emergent", "urgent", "semi_urgent", "non_urgent"],
                            "description": "Assessed acuity level",
                        },
                        "chief_complaint": {"type": "string", "description": "Main reason for visit"},
                        "is_emergency": {"type": "boolean", "description": "Whether this is an emergency"},
                    },
                    "required": ["acuity_level", "chief_complaint"],
                },
            },
        },
        # =============================================================================
        # Appointment Scheduling Tools
        # =============================================================================
        {
            "type": "function",
            "function": {
                "name": "get_available_slots",
                "description": "Get available appointment slots based on search criteria.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "specialty": {"type": "string", "description": "Provider specialty (e.g., family_medicine, cardiology)"},
                        "date_range_start": {"type": "string", "description": "Start date for search (YYYY-MM-DD)"},
                        "date_range_end": {"type": "string", "description": "End date for search (YYYY-MM-DD)"},
                        "appointment_type": {
                            "type": "string",
                            "enum": ["new_patient", "follow_up", "urgent", "telehealth"],
                            "description": "Type of appointment",
                        },
                        "location": {"type": "string", "description": "Preferred clinic location"},
                    },
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "book_appointment",
                "description": "Book an appointment for the patient using a selected slot.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "slot_id": {"type": "string", "description": "ID of the appointment slot to book"},
                        "patient_id": {"type": "string", "description": "Patient ID"},
                        "reason": {"type": "string", "description": "Reason for the visit"},
                        "notes": {"type": "string", "description": "Additional notes (optional)"},
                    },
                    "required": ["slot_id", "patient_id", "reason"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "send_appointment_confirmation",
                "description": "Send appointment confirmation to the patient via phone, email, or text.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "appointment_id": {"type": "string", "description": "Appointment ID to confirm"},
                        "patient_id": {"type": "string", "description": "Patient ID"},
                        "method": {
                            "type": "string",
                            "enum": ["phone", "email", "text"],
                            "description": "Delivery method for confirmation",
                        },
                        "phone": {"type": "string", "description": "Phone number for phone/text confirmation"},
                        "email": {"type": "string", "description": "Email address for email confirmation"},
                    },
                    "required": ["appointment_id", "patient_id"],
                },
            },
        },
        # =============================================================================
        # Session Management Tools
        # =============================================================================
        {
            "type": "function",
            "function": {
                "name": "save_intake_session",
                "description": "Save current intake session state. Use to persist progress through the intake workflow.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session identifier"},
                        "current_stage": {
                            "type": "string",
                            "enum": ["greeting", "consent", "identity", "insurance", "demographics", "triage", "scheduling", "confirmation", "completed"],
                            "description": "Current workflow stage",
                        },
                        "data": {
                            "type": "object",
                            "description": "Session data to save",
                        },
                    },
                    "required": ["session_id", "current_stage", "data"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_intake_session",
                "description": "Retrieve existing intake session state to resume a conversation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session identifier"},
                    },
                    "required": ["session_id"],
                },
            },
        },
    ]
