# Scenario Generation Pipeline Plan (Python)

## Goals
- Healthcare-only scenarios
- Multiple sources: Health Bench + Stagehand web + traces + performance failures
- Scenarios include rubric criteria and compliance metadata (state/specialty)

## Sources
1. **OpenAI Health Bench** (static subset for demo)
2. **Public websites** via Stagehand/Browser Agents (CDC, NIH)
3. **Traces/runs** (failed runs → regression scenarios)
4. **Performance** signals (latency, dropout → robustness scenarios)

## Pipeline Steps
1. **Ingest (ADK agents)**
   - Load Health Bench items
   - Extract guidelines via Stagehand (CDC/NIH)
2. **Normalize**
   - Map into canonical scenario schema
   - Attach `source_type`, `source_url`, `state`, `specialty`
3. **Generate**
   - LLM produces scenario + rubric criteria
   - Store in Redis with `rubric_hash`
4. **Review/Approve**
   - Mark as `clinician_approved` (demo uses pre-approved flag)
5. **Publish**
   - Available for test runs

## Canonical Scenario Schema (MVP)
```json
{
  "scenario_id": "sc_...",
  "title": "Chest pain w/ radiation",
  "source_type": "bench|web|trace|performance",
  "source_url": "https://...",
  "state": "CA",
  "specialty": "emergency",
  "rubric_criteria": [
    {"criterion": "Advise ER in first response", "points": 5, "tags": ["emergent"]}
  ],
  "clinician_approved": true
}
```

## Borrowed Patterns (Preclinical)
- Rubric generation flow: `preclinical/internal-docs/hackathon-scenario-pipeline.md`
- Scenario DB shape: `preclinical/internal-docs/database.md`
- Evolving scenarios: `preclinical/internal-docs/evolving-scenarios-architecture.md`

## Demo-specific Notes
- Use a tiny Health Bench subset file in `data/`
- Stagehand extracts 1 CDC/NIH guideline
- Simulated compliance change triggers new scenario generation
