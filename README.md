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
   - `./scripts/smoke.ps1` checks health, readiness, and the main smoke flow
   - `./scripts/release.ps1` runs the release checklist against a local checkout
   - `./scripts/test.ps1`
   - `./scripts/lint.ps1`
6. For a deployment-style container path, see `Dockerfile` and `docs/DEPLOYMENT.md`.

## Docs

- [Local setup](docs/LOCAL_SETUP.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [A2A mapping note](docs/A2A_MAPPING.md)
- [MVP release notes](docs/RELEASE_NOTES_MVP.md)
- [V3 release notes](docs/RELEASE_NOTES_V3.md)
- [V4 upgrade notes](docs/UPGRADE_NOTES_V4.md)
- [Runbook](docs/RUNBOOK.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Current status](STATUS.md)
- [MVP plan](PLAN.md)
- [Post-MVP plan (V2)](PLAN_V2.md)
- [V3 plan](PLAN_V3.md)
- [V4 plan](PLAN_V4.md)
- [MVP implementation backlog](IMPLEMENTATION_TASKS.md)
- [Post-MVP implementation backlog (F17-F24)](IMPLEMENTATION_TASKS_V2.md)
- [V3 implementation backlog (F25-F31)](IMPLEMENTATION_TASKS_V3.md)
- [V4 implementation backlog (F32-F35)](IMPLEMENTATION_TASKS_V4.md)
- [MVP implementation order](IMPLEMENTATION_ORDER.md)
- [Post-MVP implementation order (PR19-PR26)](IMPLEMENTATION_ORDER_V2.md)
- [V3 implementation order (PR27-PR33)](IMPLEMENTATION_ORDER_V3.md)
- [V4 implementation order (PR34-PR37)](IMPLEMENTATION_ORDER_V4.md)

## Current status

- Core coordinator, FastAPI API layer, and SQLite repository layer are in place.
- Session channels, participant roles/policies, rules, review flows, and structured permissions are in place.
- Messages, jobs, artifacts, approvals, session events, and public A2A task/event surfaces are persisted and exposed through API routes.
- Advanced job lifecycle support includes create, retry, resume, offline queueing, templates, orchestration gates, runtime pools, and streaming.
- Operator dashboard/debug surfaces and advanced policy automation are implemented.
- CodexBridge subprocess manager and JSON-RPC client are in place.
- `GET /.well-known/agent-card.json` remains available as an A2A-ready discovery placeholder.
- `GET /api/v1/readinessz` reports deployment readiness for a booted database-backed runtime.
- V4 foundation is complete through PR37, including hardening, telemetry, release readiness, and deployment readiness.
