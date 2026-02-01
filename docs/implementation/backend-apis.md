# Backend APIs Plan (Python)

## Goals
- Single Python service exposes run orchestration + status + reports.
- Stateless API with Redis as system-of-record for runs, scenarios, and state.
- Designed to support UI later.

## Suggested Framework
- FastAPI (simple, async-friendly, Python-first)

## Core Endpoints (MVP)
- `POST /runs` — create a test run
  - body: `{ target_agent_id, mode, scenario_ids[], options }`
  - returns: `{ run_id, status }`
- `GET /runs/{run_id}` — run status + summary
- `GET /runs/{run_id}/transcript` — live transcript (poll or SSE later)
- `GET /runs/{run_id}/report` — grading output + evidence
- `GET /scenarios` — list scenarios + filters (source/state/specialty)
- `POST /compliance/simulate-change` — simulate guideline update
- `GET /compliance/status` — current compliance status for target

## Run Lifecycle (state machine)
`pending → running → grading → completed | failed | canceled`

## Data Flow (MVP)
1. API creates run + writes to Redis
2. Orchestrator creates Daily room + token
3. Pipecat tester joins room and runs conversation
4. Transcript logged to Redis + Weave
5. Grader agent evaluates transcript and stores report

## Borrowed Patterns (Preclinical)
- State machine + run event logging: `preclinical/internal-docs/backend.md`
- Grading run flow: `preclinical/internal-docs/core-agents/agentic-architecture.md`
- Scenario storage shape: `preclinical/internal-docs/database.md`

## Minimal Response Shapes
```json
// GET /runs/{id}
{
  "run_id": "run_...",
  "status": "grading",
  "scenario_count": 2,
  "mode": "voice_voice",
  "started_at": 1738340000,
  "updated_at": 1738340200
}
```

```json
// GET /runs/{id}/report
{
  "break_type": "missed_emergency",
  "severity": "critical",
  "rubric_scores": [
    {"criterion_index": 0, "decision": "NOT_MET", "evidence": "..."}
  ],
  "weave_trace_id": "trace_..."
}
```
