# Observability Plan (Weave + W&B)

## Goals
- Trace all LLM calls
- Record turn-by-turn decisions
- Produce evaluation artifacts

## Weave Usage
- Initialize `weave.init(project)` in all services
- Decorate:
  - scenario generation
  - attack planning
  - tester turn decisions
  - grading evaluations

## W&B Inference
- All LLM calls go through W&B Inference API
- Store model + prompt metadata in Weave attributes

## Demo Requirements
- One full trace tree per run
- Include attack pivot decisions
- Include grading outputs

## Borrowed Patterns (Preclinical)
- Weave integration path: `preclinical/internal-docs/hackathon-scenario-pipeline.md`
