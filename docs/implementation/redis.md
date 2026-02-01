# Redis Plan

## Goals
- Single store for scenarios, runs, turn state, and learning
- Fast reads for attack-plan cache
- Pub/Sub for progress updates (UI later)

## Keyspaces
- `scenario:{id}` → scenario JSON
- `run:{id}` → run metadata
- `transcript:{run_id}` → list of turns
- `checkpoint:{run_id}` → turn state checkpoint
- `attack_plan:{scenario_id}:{rubric_hash}` → cached plan
- `vector_stats:{vector}` → effectiveness counts
- `compliance:guideline:{id}` → guideline registry entry
- `compliance:status:{target}` → certification state

## TTLs (MVP)
- attack_plan: 24h
- checkpoint: 1h
- transcripts: 7d

## Borrowed Patterns (Preclinical)
- Attack plan caching: `preclinical/internal-docs/hackathon-scenario-pipeline.md`
- Scenario + run state ideas: `preclinical/internal-docs/database.md`

## Notes
- Use `rediss://` for Redis Cloud
- Use hash keys for mutable objects (e.g., `vector_stats`)
