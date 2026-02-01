"""Grading pipeline assembly using Google ADK SequentialAgent and ParallelAgent."""

from __future__ import annotations

from google.adk.agents import ParallelAgent, SequentialAgent

from .agents import (
    QualityAssessmentAgent,
    RubricEvaluationAgent,
    SafetyAuditAgent,
    ScenarioContextAgent,
    SeverityDeterminationAgent,
    TurnAnalysisAgent,
)
from .synthesis import GradeSynthesisAgent


def build_grading_pipeline_agent() -> SequentialAgent:
    """Build the multi-step grading pipeline agent.

    Pipeline structure:
    ├── Stage 1: ScenarioContextAgent
    │   └── Understand clinical context, expectations, red flags
    ├── Stage 2: TurnAnalysisAgent
    │   └── Evaluate each conversation turn individually
    ├── Stage 3: RubricEvaluationAgent
    │   └── Score each rubric criterion with evidence
    ├── Stage 4: ParallelAgent
    │   ├── SafetyAuditAgent - Check for dangerous patterns
    │   └── QualityAssessmentAgent - Empathy, clarity, completeness
    ├── Stage 5: SeverityDeterminationAgent
    │   └── Determine overall severity and break type
    └── Stage 6: GradeSynthesisAgent
        └── Combine all results into final grade

    Returns:
        SequentialAgent: The assembled grading pipeline
    """
    # Stage 1: Understand the clinical scenario
    scenario_context_agent = ScenarioContextAgent()

    # Stage 2: Analyze each conversation turn
    turn_analysis_agent = TurnAnalysisAgent()

    # Stage 3: Score against rubric criteria
    rubric_evaluation_agent = RubricEvaluationAgent()

    # Stage 4: Parallel safety and quality assessment
    parallel_assessment = ParallelAgent(
        name="parallel_assessment",
        sub_agents=[
            SafetyAuditAgent(),
            QualityAssessmentAgent(),
        ],
    )

    # Stage 5: Determine overall severity
    severity_determination_agent = SeverityDeterminationAgent()

    # Stage 6: Synthesize final grade
    grade_synthesis_agent = GradeSynthesisAgent()

    # Assemble the pipeline
    return SequentialAgent(
        name="grading_pipeline",
        sub_agents=[
            scenario_context_agent,
            turn_analysis_agent,
            rubric_evaluation_agent,
            parallel_assessment,
            severity_determination_agent,
            grade_synthesis_agent,
        ],
    )
