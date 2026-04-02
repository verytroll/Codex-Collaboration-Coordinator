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
   - `./scripts/package_release.ps1` builds the curated small-team release bundle
   - `./scripts/release.ps1` runs the release checklist against a local checkout
   - `./scripts/test.ps1`
   - `./scripts/lint.ps1`
6. For a deployment-style container path, see `Dockerfile` and `docs/DEPLOYMENT.md`.

## Docs

- [Local setup](docs/LOCAL_SETUP.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [A2A mapping note](docs/A2A_MAPPING.md)
- [A2A compatibility matrix](docs/A2A_COMPATIBILITY_MATRIX.md)
- [MVP release notes](docs/RELEASE_NOTES_MVP.md)
- [V3 release notes](docs/RELEASE_NOTES_V3.md)
- [V5 release notes](docs/RELEASE_NOTES_V5.md)
- [V4 upgrade notes](docs/UPGRADE_NOTES_V4.md)
- [V5 upgrade notes](docs/UPGRADE_NOTES_V5.md)
- [Runbook](docs/RUNBOOK.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Operator UI shell](docs/OPERATOR_UI.md)
- [Current status](STATUS.md)
- [MVP plan](PLAN.md)
- [Post-MVP plan (V2)](PLAN_V2.md)
- [V3 plan](PLAN_V3.md)
- [V4 plan](PLAN_V4.md)
- [MVP implementation backlog](IMPLEMENTATION_TASKS.md)
- [Post-MVP implementation backlog (F17-F24)](IMPLEMENTATION_TASKS_V2.md)
- [V3 implementation backlog (F25-F31)](IMPLEMENTATION_TASKS_V3.md)
- [V4 implementation backlog (F32-F35)](IMPLEMENTATION_TASKS_V4.md)
- [V6 implementation backlog (F41-F46)](IMPLEMENTATION_TASKS_V6.md)
- [MVP implementation order](IMPLEMENTATION_ORDER.md)
- [Post-MVP implementation order (PR19-PR26)](IMPLEMENTATION_ORDER_V2.md)
- [V3 implementation order (PR27-PR33)](IMPLEMENTATION_ORDER_V3.md)
- [V4 implementation order (PR34-PR37)](IMPLEMENTATION_ORDER_V4.md)
- [V5 implementation order (PR38-PR42)](IMPLEMENTATION_ORDER_V5.md)
- [V6 implementation order (PR43-PR48)](IMPLEMENTATION_ORDER_V6.md)

## Current status

- Core coordinator, FastAPI API layer, and SQLite repository layer are in place.
- Session channels, participant roles/policies, rules, review flows, and structured permissions are in place.
- Messages, jobs, artifacts, approvals, session events, and public A2A task/event surfaces are persisted and exposed through API routes.
- Advanced job lifecycle support includes create, retry, resume, offline queueing, templates, orchestration gates, runtime pools, and streaming.
- Operator dashboard/debug surfaces and advanced policy automation are implemented.
- Thin operator UI shell is available at `/operator` and bootstraps from `/api/v1/operator/shell`.
- CodexBridge subprocess manager and JSON-RPC client are in place.
- `GET /.well-known/agent-card.json` remains available as an A2A-ready discovery placeholder.
- `GET /api/v1/readinessz` reports deployment readiness for a booted database-backed runtime.
- V4 foundation is complete through PR37, including hardening, telemetry, release readiness, and deployment readiness.
- V5 foundation is complete through PR42, including access boundary, operator UI shell, realtime operator surface, A2A interoperability, and small-team deployment packaging.
- V5 release baseline is closed through PR43 / F41, with versioned release metadata, release notes, and a synchronized verification checklist.
- V6 operator actions and audit trail are complete through PR44 / F42, with action endpoints, operator UI controls, and audited write paths.
- V6 identity and team RBAC are complete through PR45 / F43, with actor identity headers, role-gated operator/public writes, and audit enrichment.
- V6 durable runtime and persistence boundary are complete through PR46 / F44, with startup recovery, replayable queued jobs, and a packaged durable runtime loop.
- V6 realtime streaming transport is complete through PR47 / F45, with SSE resume support for operator activity and public task events.
- V6 interop certification and external adoption baseline are complete through PR48 / F46, with contract tests, compatibility claims, and sample client guidance.
