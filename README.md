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
   - `./scripts/dev.ps1` auto-applies migrations, then starts uvicorn
   - `./scripts/seed.ps1`
   - `./scripts/smoke.ps1` waits for the app to become ready, then runs a smoke test
   - `./scripts/test.ps1`
   - `./scripts/lint.ps1`

## Docs

- [Local setup](docs/LOCAL_SETUP.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [A2A mapping note](docs/A2A_MAPPING.md)
- [MVP release notes](docs/RELEASE_NOTES_MVP.md)
- [Current status](STATUS.md)
- [MVP plan](PLAN.md)
- [Post-MVP plan (V2)](PLAN_V2.md)
- [MVP implementation backlog](IMPLEMENTATION_TASKS.md)
- [Post-MVP implementation backlog (F17-F24)](IMPLEMENTATION_TASKS_V2.md)
- [MVP implementation order](IMPLEMENTATION_ORDER.md)
- [Post-MVP implementation order (PR19-PR26)](IMPLEMENTATION_ORDER_V2.md)

## Current status

- Project skeleton is in place.
- Toolchain config and `GET /api/v1/healthz` are in place.
- SQLite connection helpers and migration runner are in place.
- Session and agent API basics are in place.
- Participant and message API basics, plus session event logging, are in place.
- CodexBridge subprocess manager and JSON-RPC client are in place.
- Runtime status service and session-thread mapping service are in place.
- Message parser, mention router, and internal job creation are in place.
- Relay engine and command handlers for `/new`, `/interrupt`, and `/compact` are in place.
- Presence heartbeat, recovery, loop guard, artifacts, approvals, and SSE job/session streaming are in place.
- `GET /.well-known/agent-card.json` is available as an A2A-ready discovery placeholder.
- Post-MVP planning docs for V2 are in place.
