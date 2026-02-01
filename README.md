# AI Health Board

**Self-improving safety testing for healthcare AI agents.**

---

## Why This Exists

Healthcare AI is a **$6.9B market by 2030** with zero standardized validation.

| The Problem | The Stakes |
|-------------|------------|
| No way to evaluate AI agent safety | Misdiagnosis, missed emergencies |
| "Trust me" is the only proof | 6 states passed AI chatbot laws in 2025 |
| Point-in-time demos, then pray | California created private right of action for AI harms |
| Each buyer creates ad-hoc checklists | FDA draft guidance on AI medical devices |

**Nobody is building the "Vanta for Healthcare AI."** Until now.

---

## What It Does

A testing platform that **gets smarter with every run**.

```
Test → Grade → Learn → Improve → Test (better)
```

### Self-Improvement Mechanisms

**1. Attack Vectors Learn What Works**
- Every attack tracked with success/failure
- Redis sorted sets rank by effectiveness
- Next run uses highest-performing attacks automatically

**2. Tester Agent Evolves Strategy**
- Weave traces analyzed for patterns
- Learned overlays stored per specialty/state
- Strategic insights injected into future tests

**3. Grader Prompts A/B Tested**
- Usage and scores tracked per prompt
- Variants generated and tested
- Winners promoted automatically

**4. Compliance Adapts to Regulation**
- State-specific laws tracked (7+ states)
- Specialty guidelines monitored (CDC, NCCN)
- New scenarios generated when rules change

---

## Architecture

```
BrowserBase/HealthBench → Scenarios → Tester (text/voice/browser) → Grading Pipeline
                                              ↓                            ↓
                                         SELF-IMPROVEMENT LOOP ←───────────┘
```

---

## Quick Start

```bash
pip install -e .
uvicorn ai_health_board.api:app --port 8000
python scripts/run_local_text_test.py --scenario <id>
```

---

*Built for W&B Hackathon 2025 — Theme: Self-Improvement*
