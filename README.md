# Codex Collaboration Coordinator

Skeleton project for the coordinator service.

## Layout

- `app/` application packages
- `tests/` unit and integration tests
- `scripts/` local utility scripts

## Local setup

1. Use Python 3.11 or newer.
2. Create and activate a virtual environment.
3. Install the project in editable mode with dev dependencies when you are ready:
   `pip install -e .[dev]`
4. Copy `.env.example` to `.env` when you need local configuration.
5. Run the helper scripts:
   - `./scripts/run.ps1`
   - `./scripts/test.ps1`
   - `./scripts/lint.ps1`

## Current status

- Project skeleton is in place.
- Toolchain config and `GET /api/v1/healthz` are in place.
- SQLite connection helpers and migration runner are in place.
- Session and agent API basics are in place.
- Participant and message API basics, plus session event logging, are in place.
