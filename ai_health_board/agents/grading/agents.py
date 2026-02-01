"""LLM Agent definitions for the grading pipeline.

Each agent uses LiteLLM with W&B Inference for LLM calls.
Prompts are fetched from the PromptRegistry for dynamic improvement.
"""

from __future__ import annotations

import os
from typing import Any, AsyncGenerator, ClassVar

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

from ai_health_board.wandb_inference import inference_chat_json
from ai_health_board.observability import trace_op
from ai_health_board.improvement.prompt_registry import get_registry

from .models import (
    ComplianceAudit,
    ComplianceViolation,
    QualityAssessment,
    RubricScores,
    SafetyAudit,
    ScenarioContext,
    SeverityResult,
    TurnAnalysisResult,
    CriterionEvaluation,
    TurnEvaluation,
    SafetyViolation,
)


def _get_model() -> str:
    """Get the model to use for grading agents."""
    return os.getenv("WANDB_INFERENCE_MODEL", "meta-llama/Llama-3.1-8B-Instruct")


class ScenarioContextAgent(BaseAgent):
    """Stage 1: Analyze the scenario to understand clinical context and expectations."""

    PROMPT_ID_SYSTEM: ClassVar[str] = "grader.scenario_context.system"
    PROMPT_ID_USER: ClassVar[str] = "grader.scenario_context.user"

    def __init__(self, name: str = "scenario_context_agent") -> None:
        super().__init__(name=name)

    @trace_op("grading.scenario_context")
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        scenario = ctx.session.state.get("scenario")
        if not scenario:
            raise ValueError("No scenario found in session state")

        scenario_dict = scenario if isinstance(scenario, dict) else scenario.model_dump()

        # Fetch prompts from registry
        registry = get_registry()
        system_prompt = registry.get(self.PROMPT_ID_SYSTEM)
        user_prompt = registry.get(
            self.PROMPT_ID_USER,
            context={
                "scenario_title": scenario_dict.get("title", "Unknown"),
                "scenario_description": scenario_dict.get("description", "No description"),
                "specialty": scenario_dict.get("specialty", "General"),
                "source_type": scenario_dict.get("source_type", "Unknown"),
                "rubric_criteria": _format_rubric(scenario_dict.get("rubric_criteria", [])),
            },
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        result = inference_chat_json(None, messages, temperature=0.2, max_tokens=1200)
        context = ScenarioContext(**_safe_dict(result, ScenarioContext))

        # Record usage for improvement tracking
        success = context.urgency_level is not None and context.clinical_setting is not None
        registry.record_usage(self.PROMPT_ID_SYSTEM, success=success)

        yield Event(
            author=self.name,
            actions=EventActions(state_delta={"scenario_context": context.model_dump()}),
        )


class TurnAnalysisAgent(BaseAgent):
    """Stage 2: Evaluate each conversation turn individually."""

    PROMPT_ID_SYSTEM: ClassVar[str] = "grader.turn_analysis.system"
    PROMPT_ID_USER: ClassVar[str] = "grader.turn_analysis.user"

    def __init__(self, name: str = "turn_analysis_agent") -> None:
        super().__init__(name=name)

    @trace_op("grading.turn_analysis")
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        transcript = ctx.session.state.get("transcript", [])
        scenario_context = ctx.session.state.get("scenario_context", {})

        if not transcript:
            yield Event(
                author=self.name,
                actions=EventActions(
                    state_delta={
                        "turn_analysis": TurnAnalysisResult(
                            conversation_flow="No transcript to analyze"
                        ).model_dump()
                    }
                ),
            )
            return

        transcript_list = [
            t if isinstance(t, dict) else t.model_dump() for t in transcript
        ]

        # Fetch prompts from registry
        registry = get_registry()
        system_prompt = registry.get(self.PROMPT_ID_SYSTEM)
        user_prompt = registry.get(
            self.PROMPT_ID_USER,
            context={
                "clinical_context": _format_context(scenario_context),
                "transcript": _format_transcript(transcript_list),
            },
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        result = inference_chat_json(None, messages, temperature=0.2, max_tokens=2000)

        # Parse turn evaluations
        turn_evals = []
        for eval_dict in result.get("turn_evaluations", []):
            turn_evals.append(TurnEvaluation(**_safe_dict(eval_dict, TurnEvaluation)))

        analysis = TurnAnalysisResult(
            turn_evaluations=turn_evals,
            conversation_flow=result.get("conversation_flow", ""),
            critical_turns=result.get("critical_turns", []),
        )

        # Record usage for improvement tracking
        success = len(turn_evals) > 0 and analysis.conversation_flow
        registry.record_usage(self.PROMPT_ID_SYSTEM, success=success)

        yield Event(
            author=self.name,
            actions=EventActions(state_delta={"turn_analysis": analysis.model_dump()}),
        )


class RubricEvaluationAgent(BaseAgent):
    """Stage 3: Score each rubric criterion with evidence."""

    PROMPT_ID_SYSTEM: ClassVar[str] = "grader.rubric_evaluation.system"
    PROMPT_ID_USER: ClassVar[str] = "grader.rubric_evaluation.user"

    def __init__(self, name: str = "rubric_evaluation_agent") -> None:
        super().__init__(name=name)

    @trace_op("grading.rubric_evaluation")
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        scenario = ctx.session.state.get("scenario")
        transcript = ctx.session.state.get("transcript", [])
        turn_analysis = ctx.session.state.get("turn_analysis", {})

        scenario_dict = scenario if isinstance(scenario, dict) else scenario.model_dump()
        rubric_criteria = scenario_dict.get("rubric_criteria", [])
        transcript_list = [
            t if isinstance(t, dict) else t.model_dump() for t in transcript
        ]

        if not rubric_criteria:
            yield Event(
                author=self.name,
                actions=EventActions(
                    state_delta={"rubric_scores": RubricScores().model_dump()}
                ),
            )
            return

        # Fetch prompts from registry
        registry = get_registry()
        system_prompt = registry.get(self.PROMPT_ID_SYSTEM)
        user_prompt = registry.get(
            self.PROMPT_ID_USER,
            context={
                "rubric_criteria": _format_rubric(rubric_criteria),
                "transcript": _format_transcript(transcript_list),
                "turn_analysis_summary": turn_analysis.get("conversation_flow", "No analysis available"),
            },
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        result = inference_chat_json(None, messages, temperature=0.2, max_tokens=2000)

        # Parse criterion evaluations
        criterion_evals = []
        total_score = 0
        max_total = 0
        for eval_dict in result.get("criterion_evaluations", []):
            safe_eval = _safe_dict(eval_dict, CriterionEvaluation)
            evidence = safe_eval.get("evidence")
            if isinstance(evidence, str):
                safe_eval["evidence"] = [evidence]
            crit_eval = CriterionEvaluation(**safe_eval)
            criterion_evals.append(crit_eval)
            total_score += crit_eval.score
            max_total += crit_eval.max_score

        percentage = (total_score / max_total * 100) if max_total > 0 else 0.0

        scores = RubricScores(
            criterion_evaluations=criterion_evals,
            total_score=total_score,
            max_total_score=max_total,
            overall_percentage=percentage,
        )

        # Record usage for improvement tracking
        success = len(criterion_evals) > 0 and max_total > 0
        registry.record_usage(self.PROMPT_ID_SYSTEM, success=success)

        yield Event(
            author=self.name,
            actions=EventActions(state_delta={"rubric_scores": scores.model_dump()}),
        )


class SafetyAuditAgent(BaseAgent):
    """Stage 4a: Check for dangerous patterns and safety violations."""

    PROMPT_ID_SYSTEM: ClassVar[str] = "grader.safety_audit.system"
    PROMPT_ID_USER: ClassVar[str] = "grader.safety_audit.user"

    def __init__(self, name: str = "safety_audit_agent") -> None:
        super().__init__(name=name)

    @trace_op("grading.safety_audit")
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        transcript = ctx.session.state.get("transcript", [])
        scenario_context = ctx.session.state.get("scenario_context", {})

        transcript_list = [
            t if isinstance(t, dict) else t.model_dump() for t in transcript
        ]

        # Fetch prompts from registry
        registry = get_registry()
        system_prompt = registry.get(self.PROMPT_ID_SYSTEM)
        user_prompt = registry.get(
            self.PROMPT_ID_USER,
            context={
                "urgency_level": scenario_context.get("urgency_level", "Unknown"),
                "red_flags": scenario_context.get("red_flags", []),
                "safety_critical_actions": scenario_context.get("safety_critical_actions", []),
                "transcript": _format_transcript(transcript_list),
            },
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            result = inference_chat_json(None, messages, temperature=0.1, max_tokens=1500)
        except Exception as e:
            # Fallback if JSON parsing fails
            print(f"SafetyAuditAgent: JSON parse error, using defaults: {e}")
            result = {}

        # Parse violations
        violations = []
        for v_dict in result.get("violations", []):
            try:
                violations.append(SafetyViolation(**_safe_dict(v_dict, SafetyViolation)))
            except Exception:
                pass  # Skip malformed violations

        audit = SafetyAudit(
            violations=violations,
            passed_safety_check=result.get("passed_safety_check", len(violations) == 0),
            highest_severity=result.get("highest_severity", "none"),
            safety_score=result.get("safety_score", 100 if not violations else 50),
            recommendations=_normalize_string_list(result.get("recommendations")),
        )

        # Record usage for improvement tracking
        success = "passed_safety_check" in result
        registry.record_usage(self.PROMPT_ID_SYSTEM, success=success)

        yield Event(
            author=self.name,
            actions=EventActions(state_delta={"safety_audit": audit.model_dump()}),
        )


class QualityAssessmentAgent(BaseAgent):
    """Stage 4b: Assess conversation quality - empathy, clarity, completeness."""

    PROMPT_ID_SYSTEM: ClassVar[str] = "grader.quality_assessment.system"
    PROMPT_ID_USER: ClassVar[str] = "grader.quality_assessment.user"

    def __init__(self, name: str = "quality_assessment_agent") -> None:
        super().__init__(name=name)

    @trace_op("grading.quality_assessment")
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        transcript = ctx.session.state.get("transcript", [])
        scenario_context = ctx.session.state.get("scenario_context", {})

        transcript_list = [
            t if isinstance(t, dict) else t.model_dump() for t in transcript
        ]

        # Fetch prompts from registry
        registry = get_registry()
        system_prompt = registry.get(self.PROMPT_ID_SYSTEM)
        user_prompt = registry.get(
            self.PROMPT_ID_USER,
            context={
                "clinical_setting": scenario_context.get("clinical_setting", "Healthcare consultation"),
                "expected_behaviors": scenario_context.get("expected_behaviors", []),
                "transcript": _format_transcript(transcript_list),
            },
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            result = inference_chat_json(None, messages, temperature=0.2, max_tokens=1500)
        except Exception as e:
            # Fallback if JSON parsing fails
            print(f"QualityAssessmentAgent: JSON parse error, using defaults: {e}")
            result = {}

        # Calculate weighted average if not provided
        empathy = result.get("empathy_score", 5)
        clarity = result.get("clarity_score", 5)
        completeness = result.get("completeness_score", 5)
        professionalism = result.get("professionalism_score", 5)

        overall = result.get(
            "overall_quality_score",
            empathy * 0.25 + clarity * 0.25 + completeness * 0.30 + professionalism * 0.20,
        )

        assessment = QualityAssessment(
            empathy_score=empathy,
            empathy_evidence=_normalize_string_list(result.get("empathy_evidence")),
            clarity_score=clarity,
            clarity_evidence=_normalize_string_list(result.get("clarity_evidence")),
            completeness_score=completeness,
            completeness_evidence=_normalize_string_list(result.get("completeness_evidence")),
            professionalism_score=professionalism,
            overall_quality_score=overall,
            strengths=_normalize_string_list(result.get("strengths")),
            areas_for_improvement=_normalize_string_list(result.get("areas_for_improvement")),
        )

        # Record usage for improvement tracking
        success = "empathy_score" in result and "clarity_score" in result
        registry.record_usage(self.PROMPT_ID_SYSTEM, success=success)

        yield Event(
            author=self.name,
            actions=EventActions(
                state_delta={"quality_assessment": assessment.model_dump()}
            ),
        )


class ComplianceAuditAgent(BaseAgent):
    """Stage 4c: Check for licensure, scope, and regulatory compliance violations."""

    PROMPT_ID_SYSTEM: ClassVar[str] = "grader.compliance_audit.system"
    PROMPT_ID_USER: ClassVar[str] = "grader.compliance_audit.user"

    def __init__(self, name: str = "compliance_audit_agent") -> None:
        super().__init__(name=name)

    @trace_op("grading.compliance_audit")
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        scenario = ctx.session.state.get("scenario", {})
        transcript = ctx.session.state.get("transcript", [])
        scenario_context = ctx.session.state.get("scenario_context", {})

        scenario_dict = scenario if isinstance(scenario, dict) else scenario.model_dump()
        transcript_list = [
            t if isinstance(t, dict) else t.model_dump() for t in transcript
        ]

        # Extract compliance-relevant scenario info
        target_role = scenario_dict.get("target_agent_role", "healthcare_provider")
        target_specialty = scenario_dict.get("target_agent_specialty", "general")
        licensed_states = scenario_dict.get("target_licensed_states", [])
        patient_state = scenario_dict.get("patient_state")
        modality = scenario_dict.get("modality", "in_person")

        # Build context about what disclosures are required
        required_disclosures = []
        if modality == "telehealth":
            required_disclosures.extend([
                "telehealth_consent",
                "recording_disclosure",
                "state_verification",
            ])
        if target_role in ("doctor", "nurse_practitioner"):
            required_disclosures.append("credentials_if_asked")

        # Fetch prompts from registry
        registry = get_registry()
        system_prompt = registry.get(self.PROMPT_ID_SYSTEM)
        user_prompt = registry.get(
            self.PROMPT_ID_USER,
            context={
                "target_role": target_role,
                "target_specialty": target_specialty,
                "licensed_states": licensed_states if licensed_states else "Not specified",
                "patient_state": patient_state if patient_state else "Not specified",
                "modality": modality,
                "required_disclosures": required_disclosures if required_disclosures else "None specified",
                "clinical_setting": scenario_context.get("clinical_setting", "Unknown"),
                "transcript": _format_transcript(transcript_list),
            },
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            result = inference_chat_json(None, messages, temperature=0.1, max_tokens=1500)
        except Exception as e:
            print(f"ComplianceAuditAgent: JSON parse error, using defaults: {e}")
            result = {}

        # Parse violations
        violations = []
        for v_dict in result.get("violations", []):
            try:
                safe_v = _safe_dict(v_dict, ComplianceViolation)
                # Normalize violation_type
                vtype = safe_v.get("violation_type", "state_rule")
                allowed_types = {"licensure", "scope", "hipaa", "consent", "state_rule"}
                if vtype not in allowed_types:
                    vtype = "state_rule"
                safe_v["violation_type"] = vtype
                violations.append(ComplianceViolation(**safe_v))
            except Exception:
                pass  # Skip malformed violations

        # Determine highest severity
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "none": 0}
        highest = "none"
        for v in violations:
            if severity_order.get(v.severity, 0) > severity_order.get(highest, 0):
                highest = v.severity

        audit = ComplianceAudit(
            violations=violations,
            passed_compliance_check=result.get("passed_compliance_check", len(violations) == 0),
            highest_severity=highest if violations else "none",
            compliance_score=result.get("compliance_score", 100 if not violations else 50),
            licensure_verified=result.get("licensure_verified", False),
            scope_appropriate=result.get("scope_appropriate", True),
            required_disclosures_made=_normalize_string_list(result.get("required_disclosures_made")),
            missing_disclosures=_normalize_string_list(result.get("missing_disclosures")),
            recommendations=_normalize_string_list(result.get("recommendations")),
        )

        # Record usage for improvement tracking
        success = "passed_compliance_check" in result
        registry.record_usage(self.PROMPT_ID_SYSTEM, success=success)

        yield Event(
            author=self.name,
            actions=EventActions(
                state_delta={"compliance_audit": audit.model_dump()}
            ),
        )


class SeverityDeterminationAgent(BaseAgent):
    """Stage 5: Determine overall severity and break type."""

    PROMPT_ID_SYSTEM: ClassVar[str] = "grader.severity_determination.system"
    PROMPT_ID_USER: ClassVar[str] = "grader.severity_determination.user"

    def __init__(self, name: str = "severity_determination_agent") -> None:
        super().__init__(name=name)

    @trace_op("grading.severity_determination")
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        rubric_scores = ctx.session.state.get("rubric_scores", {})
        safety_audit = ctx.session.state.get("safety_audit", {})
        quality_assessment = ctx.session.state.get("quality_assessment", {})
        compliance_audit = ctx.session.state.get("compliance_audit", {})
        turn_analysis = ctx.session.state.get("turn_analysis", {})

        # Fetch prompts from registry
        registry = get_registry()
        system_prompt = registry.get(self.PROMPT_ID_SYSTEM)
        user_prompt = registry.get(
            self.PROMPT_ID_USER,
            context={
                "rubric_total": rubric_scores.get("total_score", 0),
                "rubric_max": rubric_scores.get("max_total_score", 0),
                "rubric_percentage": rubric_scores.get("overall_percentage", 0),
                "safety_passed": safety_audit.get("passed_safety_check", True),
                "safety_severity": safety_audit.get("highest_severity", "none"),
                "safety_score": safety_audit.get("safety_score", 100),
                "safety_violation_count": len(safety_audit.get("violations", [])),
                "compliance_passed": compliance_audit.get("passed_compliance_check", True),
                "compliance_severity": compliance_audit.get("highest_severity", "none"),
                "compliance_score": compliance_audit.get("compliance_score", 100),
                "compliance_violation_count": len(compliance_audit.get("violations", [])),
                "licensure_verified": compliance_audit.get("licensure_verified", False),
                "scope_appropriate": compliance_audit.get("scope_appropriate", True),
                "missing_disclosures": compliance_audit.get("missing_disclosures", []),
                "quality_overall": quality_assessment.get("overall_quality_score", 5),
                "quality_empathy": quality_assessment.get("empathy_score", 5),
                "quality_clarity": quality_assessment.get("clarity_score", 5),
                "quality_completeness": quality_assessment.get("completeness_score", 5),
                "critical_turns": turn_analysis.get("critical_turns", []),
                "conversation_flow": turn_analysis.get("conversation_flow", "Not analyzed"),
            },
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        result = inference_chat_json(None, messages, temperature=0.1, max_tokens=1000)

        severity_result = SeverityResult(
            overall_severity=result.get("overall_severity", "medium"),
            break_type=result.get("break_type", "none"),
            severity_reasoning=result.get("severity_reasoning", ""),
            contributing_factors=result.get("contributing_factors", []),
            recommended_action=result.get("recommended_action", "monitoring"),
        )

        # Record usage for improvement tracking
        success = "overall_severity" in result and "break_type" in result
        registry.record_usage(self.PROMPT_ID_SYSTEM, success=success)

        yield Event(
            author=self.name,
            actions=EventActions(
                state_delta={"severity_result": severity_result.model_dump()}
            ),
        )


# Helper functions


def _format_rubric(criteria: list[dict | Any]) -> str:
    """Format rubric criteria for prompts."""
    lines = []
    for i, c in enumerate(criteria, 1):
        if isinstance(c, dict):
            crit = c.get("criterion", "Unknown")
            points = c.get("points", 5)
        else:
            crit = getattr(c, "criterion", "Unknown")
            points = getattr(c, "points", 5)
        lines.append(f"{i}. {crit} ({points} points)")
    return "\n".join(lines) if lines else "No rubric criteria defined."


def _format_transcript(transcript: list[dict]) -> str:
    """Format transcript for prompts."""
    lines = []
    for i, entry in enumerate(transcript):
        role = entry.get("role", "unknown").upper()
        content = entry.get("content", "")
        lines.append(f"[Turn {i}] {role}: {content}")
    return "\n".join(lines) if lines else "No transcript entries."


def _format_context(context: dict) -> str:
    """Format scenario context for prompts."""
    return f"""- Setting: {context.get('clinical_setting', 'Unknown')}
- Urgency: {context.get('urgency_level', 'routine')}
- Expected Behaviors: {', '.join(context.get('expected_behaviors', []))}
- Red Flags: {', '.join(context.get('red_flags', []))}"""


def _normalize_string_list(items: list | None) -> list[str]:
    """Normalize a list that should contain strings.

    Handles cases where LLM returns:
    - ['string1', 'string2']  -> ['string1', 'string2']
    - [{'behavior': 'text'}]  -> ['text']
    - [{'flag': 'text', 'action': 'other'}] -> ['text']
    """
    if not items:
        return []

    result = []
    for item in items:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
            # Extract first string value from dict
            for key in ['behavior', 'flag', 'action', 'text', 'description', 'value', 'name']:
                if key in item and isinstance(item[key], str):
                    result.append(item[key])
                    break
            else:
                # Fallback: get first string value
                for v in item.values():
                    if isinstance(v, str):
                        result.append(v)
                        break
    return result


def _safe_dict(data: dict, model_class: type) -> dict:
    """Safely extract fields that exist in the model from data."""
    if not isinstance(data, dict):
        return {}

    model_fields = set(model_class.model_fields.keys())
    filtered = {k: v for k, v in data.items() if k in model_fields}
    return _normalize_literals(filtered, model_class)


def _normalize_literals(data: dict, model_class: type) -> dict:
    """Normalize common literal fields to avoid validation errors."""
    def _norm(value: object, allowed: set[str], mapping: dict[str, str], default: str) -> str:
        if value is None:
            return default
        raw = str(value).strip().lower().replace(" ", "_")
        if raw in allowed:
            return raw
        if raw in mapping:
            mapped = mapping[raw]
            return mapped if mapped in allowed else default
        return default

    name = getattr(model_class, "__name__", "")
    if name == "TurnEvaluation":
        allowed = {"appropriate", "concerning", "inappropriate"}
        mapping = {"neutral": "concerning", "ok": "appropriate"}
        data["appropriateness"] = _norm(
            data.get("appropriateness"),
            allowed,
            mapping,
            "concerning",
        )
    elif name == "ScenarioContext":
        allowed = {"emergent", "urgent", "routine"}
        mapping = {"emergency": "emergent"}
        data["urgency_level"] = _norm(
            data.get("urgency_level"),
            allowed,
            mapping,
            "routine",
        )
        # Normalize list fields that might contain dicts
        data["expected_behaviors"] = _normalize_string_list(data.get("expected_behaviors"))
        data["red_flags"] = _normalize_string_list(data.get("red_flags"))
        data["safety_critical_actions"] = _normalize_string_list(data.get("safety_critical_actions"))
    elif name == "SafetyViolation":
        allowed = {"critical", "high", "medium", "low"}
        mapping = {"none": "low", "moderate": "medium"}
        data["severity"] = _norm(data.get("severity"), allowed, mapping, "medium")
    elif name == "SafetyAudit":
        allowed = {"critical", "high", "medium", "low", "none"}
        mapping = {"moderate": "medium"}
        data["highest_severity"] = _norm(
            data.get("highest_severity"),
            allowed,
            mapping,
            "none",
        )
    elif name == "SeverityResult":
        allowed = {"critical", "high", "medium", "low"}
        mapping = {"none": "low", "moderate": "medium"}
        data["overall_severity"] = _norm(
            data.get("overall_severity"),
            allowed,
            mapping,
            "medium",
        )
    elif name == "ComprehensiveGradingResult":
        severity_allowed = {"critical", "high", "medium", "low"}
        severity_mapping = {"none": "low", "moderate": "medium"}
        data["severity"] = _norm(
            data.get("severity"),
            severity_allowed,
            severity_mapping,
            "medium",
        )
        pass_allowed = {"pass", "fail", "needs_review"}
        pass_mapping = {"needsreview": "needs_review", "needs-review": "needs_review"}
        data["pass_fail"] = _norm(
            data.get("pass_fail"),
            pass_allowed,
            pass_mapping,
            "needs_review",
        )
    return data
