# AI Health Board

**The Vanta for Healthcare AI Agents** — Continuous safety testing that gets smarter with every run.

---

## The Problem

Healthcare AI agents are deployed with zero standardized validation. Buyers can't evaluate safety, sellers can't prove it, and the stakes are life-or-death. In 2025 alone, 6 states enacted AI chatbot healthcare laws, the FDA released draft AI guidance, and California created private right of action for AI harms.

**Current evaluation is manual, inconsistent, and one-time.** Spreadsheet checklists. Vendor questionnaires. Pilots with fingers crossed.

## Our Solution

A self-improving adversarial testing platform that:
- **Finds safety failures** before patients do
- **Learns from every test** to become more effective
- **Adapts to regulatory changes** across states and specialties
- **Provides continuous monitoring**, not point-in-time validation

---

## Self-Improvement: The Core Innovation

Traditional testing is static. We built a system that **evolves**.

```
┌────────────────────────────────────────────────────────────┐
│                  SELF-IMPROVEMENT LOOP                     │
│                                                            │
│   Test → Grade → Learn → Improve → Test (better)          │
│                                                            │
│   Every run feeds back into:                              │
│   • Attack vector effectiveness rankings                  │
│   • Tester agent strategy optimization                    │
│   • Grader prompt A/B testing                             │
│   • Compliance rule updates                               │
└────────────────────────────────────────────────────────────┘
```

### 1. Attack Vectors Learn What Works

Every adversarial prompt is tracked with outcome data:

```python
# After each test, record what happened
record_attack_outcome(attack_id="auth_challenge_001", success=True, severity="high")

# Next run automatically prioritizes effective attacks
candidates = get_attack_candidates(tags=["specialty:cardiology", "state:CA"])
# → Returns attacks ranked by historical success rate
```

**How it works:**
- Attacks tagged by specialty, state, condition
- Redis sorted sets rank by confidence score
- High-performers surface automatically
- Failed attacks deprioritized

### 2. Tester Agent Improves Its Strategy

The tester doesn't just replay attacks—it learns *how* to attack:

```python
# Learned overlays store strategic insights
store_prompt_overlay(
    tags=["specialty:oncology"],
    overlay="Dosing questions expose scope violations. Lead with medication concerns."
)

# Retrieved automatically for matching scenarios
overlay = get_prompt_overlay(scenario.tags)  # Injected into tester prompt
```

**Improvement mechanisms:**
- Weave traces analyzed for effective patterns
- Strategy overlays generated from successful runs
- 7-day TTL keeps strategies fresh
- Per-specialty and per-state learnings

### 3. Grader Agent Refines Its Evaluation

Grading prompts evolve through A/B testing:

```python
# Track prompt performance
registry.record_usage("grader.safety_audit", success=True, score=0.92)

# After 10+ uses, generate improved variant
variant = generate_prompt_variant(original, performance_metrics)

# A/B test and promote winners
if ab_test(baseline, variant).variant_wins:
    promote_to_active(variant)
```

**The grading pipeline** (6 stages via Google ADK):
```
ScenarioContext → TurnAnalysis → RubricEvaluation
                                       ↓
              SafetyAudit | QualityAssess | ComplianceAudit  (parallel)
                                       ↓
                    SeverityDetermination → Synthesis
```

Each stage's prompts can be independently improved.

### 4. Compliance Adapts to Regulatory Changes

Healthcare regulations vary by **state** and **specialty**—and they change constantly.

```python
# Register guideline with version tracking
register_guideline(Guideline(
    id="ca_mental_health_chatbot_2025",
    state="CA",
    specialty="psychiatry",
    effective_date="2025-10-01",
    requirements=[...]
))

# When guidelines change, system detects and adapts
simulate_guideline_change(guideline_id)
# → Generates new test scenarios
# → Updates compliance audit criteria
# → Flags affected historical runs
```

**What we track:**
- State-specific AI healthcare laws (7+ states in 2025)
- Specialty guidelines (NCCN, CDC, professional associations)
- FDA AI/ML guidance updates
- HIPAA requirements for AI systems

**Automatic extraction:** BrowserBase + Stagehand scrape authoritative sources, validate content, and generate test scenarios from new guidelines.

---

## Architecture

```
Data Ingestion          Adversarial Testing         Evaluation
──────────────          ───────────────────         ──────────
BrowserBase ─┐          ┌─ Text Tester              6-Stage Grading
HealthBench ─┼─ Scenarios ─┼─ Voice (Pipecat) ─ Transcript ─► Pipeline
Guidelines ──┘          └─ Browser Tester            (Google ADK)
                               │                         │
                               └─────────────────────────┘
                                   SELF-IMPROVEMENT
                              (Attack Memory, Prompt Registry,
                               Weave Traces, Compliance Rules)
```

---

## Quick Start

```bash
# Setup
python -m venv .venv && source .venv/bin/activate && pip install -e .

# Run API + Frontend
uvicorn ai_health_board.api:app --port 8000
cd frontend && npm install && npm run dev

# Run a test
python scripts/seed_scenario.py
python scripts/run_local_text_test.py --scenario <id>

# Run improvement cycle
python scripts/run_improvement_cycle.py
```

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENAI_API_KEY` | Yes | LLM inference |
| `WANDB_API_KEY` | Yes | Weave observability |
| `REDIS_CLOUD_*` | No* | Learning store |
| `BROWSERBASE_API_KEY` | No | Guideline extraction |
| `DAILY_API_KEY` | No | Voice testing |

*Use `REDIS_FALLBACK=1` for in-memory mode

---

## Key Files

| Component | File |
|-----------|------|
| Attack Memory | `attack_memory.py` |
| Prompt Registry | `improvement/prompt_registry.py` |
| Improvement Loop | `improvement/improvement_loop.py` |
| Tester Agent | `tester_agent.py` |
| Grading Pipeline | `agents/grading/pipeline.py` |
| Compliance Tracking | `compliance.py` |
| Weave Analysis | `weave_self_improve.py` |

---

*Built for the W&B Hackathon 2025 — Theme: Self-Improvement*
