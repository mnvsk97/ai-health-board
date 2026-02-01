# Tester Agent Plan (Python, evolving)

## Goals
- Pen-test healthcare AI agents
- Evolve over time (non-static)
- Use W&B Inference for LLM calls
- Track effectiveness in Redis

## Core Components
1. **Attack Planner**
   - Analyzes scenario rubric criteria
   - Produces multi-phase attack plan
2. **Adaptive Tester**
   - Runs turn-by-turn
   - Uses per-turn evaluation to pivot vectors
3. **Learning Loop**
   - Track vector effectiveness
   - Prioritize effective vectors in future runs

## Evolving Mechanism (MVP)
- Store per-vector stats in Redis:
  - `attempted`, `effective`
- Maintain `vector_rank` sorted by effectiveness
- New run selects top vectors first

## Turn State
- `current_turn`, `vector_index`, `pivot_history`, `criteria_signals`
- Persist checkpoints to Redis each turn

## Borrowed Patterns (Preclinical)
- Pen-testing flow: `preclinical/internal-docs/core-agents/agentic-architecture.md`
- Attack-plan cache + pivot logic: `preclinical/internal-docs/hackathon-scenario-pipeline.md`

## Minimal Interface
```python
def plan_attack(scenario) -> dict: ...
def next_message(scenario, target_response, plan, turn_index) -> str: ...
def init_turn_state() -> dict: ...
def advance_turn(state) -> None: ...
```

## Demo behavior
- Start with emergent/safety vectors
- Pivot when evaluation indicates resistance
- Log all decisions to Weave
