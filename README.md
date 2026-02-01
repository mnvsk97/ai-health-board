# AI Health Board

**Self-Improving Preclinical Testing for Healthcare AI Agents**

A platform that tests healthcare AI agents and *gets smarter with every test run*. The system learns which attack strategies expose safety violations, improves its prompts through A/B testing, and continuously refines its evaluation criteria.

---

## The Self-Improvement Loop

This is the core innovation. Traditional AI testing is static—you write tests, run them, done. AI Health Board creates a **continuous learning cycle**:

```
┌─────────────────────────────────────────────────────────────────┐
│                    SELF-IMPROVEMENT LOOP                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────┐      ┌──────────┐      ┌──────────┐            │
│   │  Test    │─────►│  Grade   │─────►│  Learn   │            │
│   │  Agent   │      │  Results │      │  Patterns│            │
│   └──────────┘      └──────────┘      └────┬─────┘            │
│        ▲                                   │                   │
│        │                                   ▼                   │
│        │            ┌──────────────────────────────┐          │
│        │            │  IMPROVEMENT ENGINE          │          │
│        │            │  • Attack memory ranking     │          │
│        │            │  • Prompt A/B testing        │          │
│        │            │  • Strategy overlays         │          │
│        │            │  • Weave trace analysis      │          │
│        │            └──────────────┬───────────────┘          │
│        │                           │                           │
│        └───────────────────────────┘                          │
│              Better attacks next run                           │
└─────────────────────────────────────────────────────────────────┘
```

### How It Self-Improves

**1. Attack Memory Learning** (`attack_memory.py`)
- Every attack is tagged (specialty, condition, state)
- Outcomes tracked: attempts, successes, severity triggered
- Redis sorted sets rank attacks by effectiveness per tag
- Next run automatically uses highest-performing attacks

```python
# After each test
record_attack_outcome(attack_id, success=True, severity="high")

# Next run retrieves best attacks for this scenario type
candidates = get_attack_candidates(tags=["specialty:cardiology"])
# Returns attacks ranked by historical success rate
```

**2. Prompt A/B Testing** (`improvement/improvement_loop.py`)
- System prompts tracked with usage counts and scores
- After 10+ uses, generates improved variants via LLM
- A/B tests variants against baseline
- Winners automatically promoted

```python
# Analyze prompt performance
analysis = analyze_prompt_performance("grader.safety_audit.system")

# Generate and test variant
variant = generate_prompt_variant(original, performance_data)
results = ab_test(baseline, variant)

# Promote if better
if results.variant_wins:
    promote_to_active(variant)
```

**3. Learned Strategy Overlays** (`attack_memory.py`)
- Stores strategic guidance from successful runs
- Retrieved during attack planning
- 7-day TTL, continuously refreshed

```python
# Store learned insight
store_prompt_overlay(
    tags=["specialty:cardiology"],
    overlay="Emphasize medication dosing questions—high success rate"
)

# Retrieved automatically in next cardiology test
overlay = get_prompt_overlay(scenario_tags)
```

**4. Weave Trace Analysis** (`weave_self_improve.py`)
- Queries historical traces from W&B Weave
- Identifies patterns in effective vs ineffective attacks
- Generates improved strategies from real data

---

## Architecture Overview

```
Data Sources                    Testing                      Evaluation
─────────────                   ───────                      ──────────
┌────────────┐                 ┌────────────┐               ┌────────────┐
│ BrowserBase│──┐              │Text Tester │──┐            │ 6-Stage    │
│ Guidelines │  │  Scenarios   │Voice Tester│  │ Transcript │ Grading    │
├────────────┤  ├────────────► │Browser Test│──┼──────────► │ Pipeline   │
│ HealthBench│  │              └────────────┘  │            │ (ADK)      │
│ Dataset    │──┘                    ▲         │            └─────┬──────┘
└────────────┘                       │         │                  │
                                     │         │                  ▼
                              ┌──────┴─────────┴──────────────────────┐
                              │         SELF-IMPROVEMENT              │
                              │  Attack Memory → Prompt Registry →    │
                              │  Weave Traces → Strategy Overlays     │
                              └───────────────────────────────────────┘
```

---

## Key Components

| Component | Purpose | Self-Improvement Role |
|-----------|---------|----------------------|
| **Attack Memory** | Stores adversarial prompts with effectiveness stats | Ranks attacks by historical success |
| **Prompt Registry** | Versioned prompt storage with metrics | Enables A/B testing and promotion |
| **Weave Integration** | Full observability of all operations | Source data for learning patterns |
| **Grading Pipeline** | 6-stage evaluation (safety, quality, compliance) | Provides scores for improvement loop |

### Grading Pipeline (Google ADK)

Sequential + parallel agent architecture:

```
ScenarioContext → TurnAnalysis → RubricEvaluation
                                       ↓
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
               SafetyAudit      QualityAssess      ComplianceAudit
                    └──────────────────┼──────────────────┘
                                       ↓
                         SeverityDetermination → Synthesis
```

### Testing Modes

- **Text-only**: Fast iteration, API-based
- **Voice (Pipecat)**: Real speech via Daily.co + Cartesia TTS
- **BrowserBase**: Test web-based AI chat interfaces

---

## Redis as the Learning Store

Redis powers the self-improvement system:

| Key Pattern | Purpose |
|-------------|---------|
| `attack:stats:{id}` | Attempts, successes, severity per attack |
| `attack:tag:{tag}` | Sorted set of attacks ranked by confidence |
| `prompt:registry:{key}` | Versioned prompts with performance metrics |
| `prompt:overlay:{tags}` | Learned strategies (7-day TTL) |
| `scenario:{id}` | Scenarios with vector embeddings |
| `grading:{id}` | Grading results feeding improvement |

---

## Quick Start

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Configure .env (see Environment Variables below)

# Run API
uvicorn ai_health_board.api:app --reload --port 8000

# Run a test
python scripts/seed_scenario.py
python scripts/run_local_text_test.py --scenario <id>

# Run improvement cycle
python scripts/run_improvement_cycle.py
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | LLM inference |
| `WANDB_API_KEY` | Yes | Weave observability |
| `REDIS_CLOUD_*` | No* | Redis Cloud connection |
| `DAILY_API_KEY` | No** | Voice testing |
| `CARTESIA_API_KEY` | No** | TTS for voice |
| `BROWSERBASE_API_KEY` | No*** | Browser automation |

\* Use `REDIS_FALLBACK=1` for in-memory mode
\** Required for voice testing
\*** Required for guideline extraction

---

## Key Files

| File | Purpose |
|------|---------|
| `attack_memory.py` | Attack effectiveness tracking & ranking |
| `improvement/improvement_loop.py` | Prompt A/B testing engine |
| `improvement/prompt_registry.py` | Versioned prompt storage |
| `weave_self_improve.py` | Trace analysis for learning |
| `tester_agent.py` | Adversarial test generation |
| `agents/grading/pipeline.py` | Multi-stage grading |
| `redis_store.py` | Central data & learning store |

---

Built for the W&B Preclinical Hackathon 2025 — *Theme: Self-Improvement*
