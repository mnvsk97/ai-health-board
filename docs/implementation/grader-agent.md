# Grader Agent Plan (Python)

## Goals
- Rubric-based grading of transcripts
- Identify break type + severity
- Produce audit-ready evidence

## Inputs
- Scenario (with rubric_criteria)
- Transcript (turns + timestamps)

## Outputs
- Per-criterion decision (MET / NOT_MET)
- Severity (critical/high/medium/low)
- Break type (missed emergency, unsafe advice, PHI leak)

## LLM Usage
- W&B Inference API for grading calls
- Weave tracing for evaluation lineage

## Borrowed Patterns (Preclinical)
- Grader shape + rubric evaluation: `preclinical/internal-docs/core-agents/agentic-architecture.md`
- Grading evaluation loop: `preclinical/internal-docs/hackathon-scenario-pipeline.md`

## Minimal Output Schema
```json
{
  "grader_model": "gpt-4o-mini",
  "evaluations": [
    {"criterion_index": 0, "decision": "NOT_MET", "evidence": "..."}
  ],
  "break_type": "missed_emergency",
  "severity": "critical"
}
```
