# Repository Guidelines

## Project Structure & Module Organization
- `main.py` is the current entry point for the app logic.
- `docs/` holds product and design documentation (see `docs/prd.md`).
- `README.md` is currently empty and should be updated as the project grows.
- The repository is early-stage and may evolve; keep new modules small and colocate related code.

## Build, Test, and Development Commands
- `python -m venv .venv` and `source .venv/bin/activate` to create/activate a local virtualenv.
- `pip install -r requirements.txt` once dependencies are captured (not yet present).
- `pytest` runs the test suite (framework is expected even if tests are not yet added).
- `ruff check .` (or `ruff check --fix .`) for linting.
- `mypy .` for static type checks.

## Coding Style & Naming Conventions
- Python 3.12 is the target runtime (see `pyproject.toml`).
- Follow PEP 8 with 4-space indentation and snake_case for modules/functions.
- Prefer explicit, descriptive names (e.g., `health_score_model.py`, `load_patient_data`).
- Use Ruff for linting and mypy-compatible type hints where practical.
- Avoid OOP unless absolutely required; prefer simple functions and data structures.

## Testing Guidelines
- Use `pytest` for unit tests.
- Place tests in `tests/` and name files `test_*.py` (e.g., `tests/test_scoring.py`).
- Aim for coverage on core logic; add fixtures for external integrations.

## Commit & Pull Request Guidelines
- No established commit convention yet (only an initial commit exists). Use concise, imperative messages (e.g., “Add risk scoring pipeline”).
- PRs should include a clear description, linked issue (if any), and notes on how to test.
- Include screenshots or logs when changes affect UI/CLI outputs.

## Security & Configuration Tips
- Keep secrets out of source control. Use `.env` or local config files for credentials.
- Document required env vars in `README.md` or `docs/` as they are introduced.
- Before asking for secrets or halting a task due to missing env vars, first check `.env` for required keys.

## Agent-Specific Notes
- This repo uses Abstra and Marimo; prefer lightweight scripts and notebooks for experiments, then promote stable logic into Python modules.
- Update `docs/prd.md` when user-facing behavior changes.
- Track completed work and implementation progress continuously in a doc (create/update `docs/implementation/progress.md`).
- Always update `docs/implementation/progress.md` when finishing a task or milestone before responding.
