from __future__ import annotations

import asyncio
import time as time_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .agents.grading.models import ComprehensiveGradingResult
from .models import Scenario, TranscriptEntry
from .observability import trace_attrs


def grade_transcript_comprehensive(
    scenario: Scenario, transcript: list[TranscriptEntry]
) -> "ComprehensiveGradingResult":
    """Grade a transcript using the comprehensive multi-step pipeline."""
    scenario_data = scenario.model_dump(mode="json")
    transcript_data = [t.model_dump(mode="json") for t in transcript]
    result_dict = _grade_transcript_comprehensive_safe(scenario_data, transcript_data)
    from .agents.grading.models import ComprehensiveGradingResult
    return ComprehensiveGradingResult(**result_dict)


async def grade_transcript_comprehensive_async(
    scenario: Scenario, transcript: list[TranscriptEntry]
) -> "ComprehensiveGradingResult":
    """Async version of grade_transcript_comprehensive."""
    scenario_data = scenario.model_dump(mode="json")
    transcript_data = [t.model_dump(mode="json") for t in transcript]
    result_dict = await _grade_transcript_comprehensive_safe_async(
        scenario_data, transcript_data
    )
    from .agents.grading.models import ComprehensiveGradingResult
    return ComprehensiveGradingResult(**result_dict)


def _grade_transcript_comprehensive_safe(
    scenario_data: dict, transcript_data: list[dict]
) -> dict:
    scenario = Scenario(**scenario_data)
    transcript = [TranscriptEntry(**t) for t in transcript_data]
    with trace_attrs(
        {
            "grading.scenario_id": scenario.scenario_id,
            "grading.transcript_len": len(transcript),
        }
    ):
        result = asyncio.run(_run_grading_pipeline(scenario, transcript))
        return result.model_dump(mode="json")


async def _grade_transcript_comprehensive_safe_async(
    scenario_data: dict, transcript_data: list[dict]
) -> dict:
    scenario = Scenario(**scenario_data)
    transcript = [TranscriptEntry(**t) for t in transcript_data]
    with trace_attrs(
        {
            "grading.scenario_id": scenario.scenario_id,
            "grading.transcript_len": len(transcript),
        }
    ):
        result = await _run_grading_pipeline(scenario, transcript)
        return result.model_dump(mode="json")


async def _run_grading_pipeline(
    scenario: Scenario, transcript: list[TranscriptEntry]
) -> "ComprehensiveGradingResult":
    """Execute the ADK grading pipeline.

    Args:
        scenario: The scenario being evaluated
        transcript: List of transcript entries

    Returns:
        ComprehensiveGradingResult from the pipeline
    """
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    from .agents.grading.pipeline import build_grading_pipeline_agent

    # Build the grading pipeline agent
    pipeline = build_grading_pipeline_agent()

    # Prepare initial state with scenario and transcript
    session_id = f"grading_{scenario.scenario_id}_{int(time_module.time())}"
    initial_state = {
        "scenario": scenario.model_dump(),
        "transcript": [t.model_dump() for t in transcript],
    }

    # Create session service and session
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="grading_pipeline",
        user_id="grader",
        session_id=session_id,
        state=initial_state,
    )

    # Create runner
    runner = Runner(
        agent=pipeline,
        app_name="grading_pipeline",
        session_service=session_service,
    )

    # Run the pipeline
    final_state = initial_state.copy()
    async for event in runner.run_async(
        user_id="grader",
        session_id=session_id,
        new_message=types.Content(parts=[types.Part(text="Grade transcript")]),
    ):
        # Collect state updates from events
        if hasattr(event, "actions") and event.actions:
            state_delta = getattr(event.actions, "state_delta", None)
            if state_delta:
                final_state.update(state_delta)

    # Extract the comprehensive result from final state
    from .agents.grading.models import ComprehensiveGradingResult

    result_dict = final_state.get("comprehensive_grading_result")
    if result_dict:
        return ComprehensiveGradingResult(**result_dict)

    # Fallback if pipeline didn't produce expected output
    from .agents.grading.models import (
        QualityAssessment,
        RubricScores,
        SafetyAudit,
        ScenarioContext,
        SeverityResult,
        TurnAnalysisResult,
    )
    return ComprehensiveGradingResult(
        grader_model="wandb_inference_pipeline",
        scenario_id=scenario.scenario_id,
        grading_timestamp=time_module.time(),
        scenario_context=ScenarioContext(
            clinical_setting="unknown",
            patient_presentation="unknown",
        ),
        turn_analysis=TurnAnalysisResult(),
        rubric_scores=RubricScores(),
        safety_audit=SafetyAudit(),
        quality_assessment=QualityAssessment(),
        severity_result=SeverityResult(
            overall_severity="medium",
            break_type="pipeline_error",
            severity_reasoning="Pipeline did not produce expected output",
        ),
        break_type="pipeline_error",
        severity="medium",
        evaluations=[],
        final_score=0.0,
        pass_fail="needs_review",
    )
