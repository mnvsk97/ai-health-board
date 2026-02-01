# Frontend Plan (Later)

## Scope
- Minimal dashboard for demo
- Real-time transcript + grading results
- Compliance status + update notification

## Screens
1. **Dashboard**
   - Target agent selector
   - Mode toggle (text↔text / text↔voice / voice↔voice)
   - Scenario list with tags
   - Run button

2. **Run Detail**
   - Live transcript
   - Break events highlighted
   - Grading summary

3. **Compliance Panel**
   - Certification status
   - Guideline update notifications

## Realtime
- Redis Pub/Sub → WebSocket/SSE
- Run progress + transcript streaming

## Tech (suggested)
- Next.js + Tailwind
- API from FastAPI backend

## Borrowed Patterns (Preclinical)
- UI layout references: `preclinical/internal-docs/current_ui.md`
