# PRD — Preclinical Standard v1 (Healthcare AI Agents)

## Vision
Create the **Vanta/Drata/Delve for healthcare AI agents**: continuous safety and compliance testing with audit-ready evidence. There is no accepted standard to grade healthcare AI agents today. Preclinical defines and enforces that standard.

## Problem
- Buyers cannot evaluate healthcare AI vendors beyond demos.
- Sellers cannot prove safety, compliance, or reliability.
- Regulatory guidance is fragmented and evolving by state and specialty.

## Solution
A healthcare-only certification platform that:
1) Ingests medical benchmarks + public guidelines
2) Generates clinician-approved scenarios + rubrics
3) Runs adaptive pen-testing against voice/chat agents
4) Grades with rubric-based evidence and outputs compliance status
5) Detects guideline changes and invalidates certifications

## Product Pillars
1. **Continuous Controls Testing**
2. **Audit-Ready Evidence**
3. **Evolving Adversarial Testing**

## Standard Definition
**Preclinical Standard v1** = clinician-approved scenario library + rubric scoring + evidence pack. Certification is valid until expiration **or** a relevant guideline update.

## Scope (Hackathon)
- Sources: OpenAI Health Bench + Stagehand (CDC/NIH)
- Python-only backend and agents
- Pipecat-only target + tester agents
- W&B Inference + Weave tracing
- Redis as system-of-record

## Success Criteria (MVP)
- End-to-end run against target agent (voice or text)
- Grading output with break type + severity
- Compliance change triggers revalidation
- Evidence trace in Weave

## Non-Goals (Hackathon)
- Enterprise auth
- Full compliance certification
- Large-scale UI

## Risks
- Guideline changes are complex → demo uses simulated update
- Grading consistency → combine rubric + evidence

## Metrics
- Scenarios generated per source
- Break rate + severity
- Time-to-break

## Roadmap (Post-hackathon)
- Multi-tenant UI
- Expanded guideline database
- Clinician review workflow
