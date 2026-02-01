# Compliance Updates Plan

## Goal
Demonstrate guideline change detection that invalidates certification and triggers new scenarios.

## Registry Model (Redis)
```json
{
  "guideline_id": "cdc_emergent_v1",
  "source_url": "https://www.cdc.gov/...",
  "state": "CA",
  "specialty": "emergency",
  "version": "2026-01-31",
  "hash": "...",
  "last_checked": 1738340000
}
```

## Change Detection (MVP)
- Daily/scheduled check: fetch source URL → hash → compare
- If hash changes:
  - mark compliance status `outdated`
  - generate 1–2 new scenarios
  - notify UI (later) or log event

## Demo Mechanism
- `POST /compliance/simulate-change` updates hash/version
- UI toast: “Guideline updated → revalidation required”

## Certification Rules
- Certification valid until `expires_at` OR guideline update
- If guideline changes: status → `outdated`

## Borrowed Patterns (Preclinical)
- Regulatory DB direction: `preclinical/internal-docs/business/market-research.md`
