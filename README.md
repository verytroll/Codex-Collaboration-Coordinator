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
   - `./scripts/docs_check.ps1` validates docs registry coverage and metadata references
   - `./scripts/test.ps1`
   - `./scripts/lint.ps1`
6. For a deployment-style container path, see `Dockerfile` and `docs/operations/DEPLOYMENT.md`.

## Docs

- [Docs index](docs/README.md)
- [Planning index](docs/planning/INDEX.md)
- [Reference index](docs/reference/INDEX.md)
- [Planning archive](docs/planning/archive/INDEX.md)
- [Current status](docs/planning/STATUS.md)
- [Active V7 plan](docs/planning/PLAN_V7.md)
- [Active V7 implementation backlog](docs/planning/IMPLEMENTATION_TASKS_V7.md)
- [Active V7 implementation order](docs/planning/IMPLEMENTATION_ORDER_V7.md)
- [Local setup](docs/operations/LOCAL_SETUP.md)
- [Runbook](docs/operations/RUNBOOK.md)
- [Deployment](docs/operations/DEPLOYMENT.md)
- [Operator UI shell](docs/operator/OPERATOR_UI.md)
- [Troubleshooting](docs/operations/TROUBLESHOOTING.md)
- [A2A mapping note](docs/integrations/a2a/A2A_MAPPING.md)
- [A2A compatibility matrix](docs/integrations/a2a/A2A_COMPATIBILITY_MATRIX.md)
- [MVP release notes](docs/releases/RELEASE_NOTES_MVP.md)
- [V3 release notes](docs/releases/RELEASE_NOTES_V3.md)
- [V5 release notes](docs/releases/RELEASE_NOTES_V5.md)
- [V6 release notes](docs/releases/RELEASE_NOTES_V6.md)
- [V7 release notes](docs/releases/RELEASE_NOTES_V7.md)
- [V4 upgrade notes](docs/releases/UPGRADE_NOTES_V4.md)
- [V5 upgrade notes](docs/releases/UPGRADE_NOTES_V5.md)
- [V6 upgrade notes](docs/releases/UPGRADE_NOTES_V6.md)
- [V7 upgrade notes](docs/releases/UPGRADE_NOTES_V7.md)
- [PRD](docs/reference/PRD.md)
- [Architecture](docs/reference/ARCHITECTURE.md)
- [API reference](docs/reference/API.md)
- [Database schema](docs/reference/DB_SCHEMA.md)
- [Borrowed ideas](docs/reference/BORROWED_IDEAS.md)

## Current status

- Core coordinator, FastAPI API layer, and SQLite repository layer are in place.
- Session channels, participant roles/policies, rules, review flows, and structured permissions are in place.
- Messages, jobs, artifacts, approvals, session events, and public A2A task/event surfaces are persisted and exposed through API routes.
- Advanced job lifecycle support includes create, retry, resume, offline queueing, templates, orchestration gates, runtime pools, and streaming.
- Managed outbound webhook delivery is available for public A2A task events, with retry, recovery, and operator visibility.
- Contract governance and early-adopter conformance are defined for the supported public A2A surface, with a repeatable verifier script.
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
- V6 release baseline is closed through PR49 / F47, with versioned release metadata, release notes, and a synchronized verification checklist.
- V7 release closure and early-adopter handoff are complete through PR55 / F53, with a versioned `0.4.0` baseline, release notes, upgrade notes, and a repeatable release gate.

