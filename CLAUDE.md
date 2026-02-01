# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Health Board - A Python-based AI automation project using the Abstra framework with Marimo notebooks for interactive data analysis.

## Technology Stack

- **Language**: Python
- **Framework**: Abstra (AI-powered process automation)
- **Notebooks**: Marimo (reactive Python notebooks)
- **Package Management**: pip/uv/poetry
- **Testing**: pytest
- **Linting**: Ruff
- **Type Checking**: mypy

## Development Commands

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Unix/macOS

# Install dependencies (once requirements exist)
pip install -r requirements.txt

# Run tests
pytest

# Run single test file
pytest tests/test_file.py

# Run specific test
pytest tests/test_file.py::test_function_name

# Linting
ruff check .
ruff check --fix .

# Type checking
mypy .
```

## Environment Variables

All required API keys and configuration are stored in `.env`. Before asking the user about missing keys or halting execution:

1. **Always check `.env` first** - The file contains all necessary credentials
2. **Assume keys exist** - If code references an env var, it's configured in `.env`
3. **Never halt for missing keys** - Proceed with implementation; the keys are there

Key environment variables available:
- `BROWSERBASE_API_KEY`, `BROWSERBASE_PROJECT_ID` - Browser automation
- `WANDB_API_KEY`, `WANDB_ENTITY`, `WANDB_PROJECT` - W&B/Weave observability
- `REDIS_CLOUD_HOST`, `REDIS_CLOUD_PORT`, `REDIS_CLOUD_PASSWORD` - Redis storage
- `OPENAI_API_KEY`, `OPENAI_BASE_URL` - LLM inference
- `DAILY_API_KEY`, `DAILY_DOMAIN` - Daily.co for voice
- `CARTESIA_API_KEY`, `CARTESIA_VOICE_ID` - Cartesia TTS
- `PIPECAT_CLOUD_API_KEY`, `PIPECAT_CLOUD_PROJECT_ID` - Pipecat deployment

## Project Status

This repository is in its initial phase. The architecture and structure will be documented here as the project develops.
