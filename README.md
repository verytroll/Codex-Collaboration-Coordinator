# Codex Collaboration Coordinator

Multi-agent coordination system for session-based collaboration, routing, review, and job orchestration.

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

- Core coordinator, FastAPI API layer, and SQLite repository layer are in place.
- Session channels, participant roles/policies, and structured permissions are in place.
- Messages, jobs, artifacts, approvals, and session events are persisted and exposed through API routes.
- Advanced job lifecycle support includes create, retry, resume, offline queueing, and streaming.
- Rules engine, manual activation flow, transcript export, and review mode are implemented.
- Structured relay templates support planner, builder, and reviewer handoffs.
- Session phase presets and the experimental A2A adapter bridge are implemented.
- CodexBridge subprocess manager and JSON-RPC client are in place.
- `GET /.well-known/agent-card.json` remains available as an A2A-ready discovery placeholder.
- Post-MVP V2 foundation is complete; V3 planning is next.
