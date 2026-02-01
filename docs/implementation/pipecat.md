# Pipecat Plan (Tester + Target)

## Goals
- Pipecat-only execution path
- Support text↔text, text↔voice, voice↔voice
- One room per run (parallelism)

## Target Agent
- Deployed to Pipecat Cloud
- Provides healthcare-specific behavior (triage, scheduling, intake)

## Tester Agent
- Runs in Pipecat pipeline with adaptive pen-tester processor
- Uses W&B Inference for next-message generation
- Logs every turn to Weave + Redis

## Daily Rooms
- Create rooms dynamically using Daily API
- Per-run: create room, create token, join, run, teardown
- Room URL format: `https://{DAILY_DOMAIN}.daily.co/{room_name}`

## Modes
- **text↔text**: no STT/TTS
- **text↔voice**: TTS on, STT off
- **voice↔voice**: STT + TTS on

## Borrowed Patterns (Preclinical)
- Pipecat integration flow: `preclinical/internal-docs/pipecat/README.md`

## Dependencies
- Pipecat
- Daily API
- Cartesia TTS
- STT provider (if needed for voice input)
