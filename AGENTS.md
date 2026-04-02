# AGENTS.md

## 1. Project Overview

This project is **Codex Collaboration Coordinator**.

It is a multi-agent coordination system that:
- manages sessions
- routes messages between agents
- integrates with Codex app-server
- supports mention-based collaboration (`#agent`)

Core architecture:
- coordinator-first
- Codex is the execution engine via `CodexBridge`
- session + agent + message + job + artifact model

## 2. Tech Stack

- Python 3.11+
- FastAPI
- SQLite for the current baseline
- async/await for I/O paths

Do not:
- use Flask
- introduce blocking I/O in request or service paths
- add dependencies without a concrete reason

## 3. Repository Structure

Main code:
- `app/api/` thin HTTP routes and request wiring
- `app/services/` business logic and orchestration
- `app/repositories/` persistence access
- `app/models/` API and domain models
- `app/codex_bridge/` Codex bridge integration
- `app/core/` config, middleware, logging, telemetry, versioning
- `app/db/` database connection and migrations
- `ui/` operator-facing static UI assets

Docs:
- `docs/planning/` status, plans, implementation backlog, implementation order
- `docs/reference/` PRD, architecture, API, schema, strategy references
- `docs/operations/`, `docs/operator/`, `docs/integrations/`, `docs/releases/`, `docs/features/`
- `docs/_meta/documents.yaml` canonical docs metadata registry

Tests:
- `tests/unit/`
- `tests/integration/`

Do not:
- mix business logic inside API routes
- bypass repositories from API handlers
- write raw SQL in services

## 4. Context Discipline

Assume the agent has a large but still limited context window. Do not load the entire docs history by default.

Read in this order:
1. `README.md`
2. `docs/planning/INDEX.md`
3. `docs/planning/STATUS.md`
4. The active phase docs named by `docs/planning/STATUS.md`
5. `docs/reference/INDEX.md` only if deeper product, contract, schema, or architecture context is needed
6. Only the specific code, tests, and domain docs touched by the task

Rules:
- do not read every `PLAN*`, `IMPLEMENTATION_TASKS*`, and `IMPLEMENTATION_ORDER*` file unless the task explicitly depends on historical progression
- do not read `docs/planning/archive/` by default
- use `rg` to find the exact module, route, test, or doc section before opening long files
- prefer targeted reads from long files over full-file reads when possible
- treat `docs/planning/STATUS.md` as the routing document for which phase matters now
- use `docs/reference/ARCHITECTURE.md`, `docs/reference/API.md`, and `docs/reference/DB_SCHEMA.md` selectively for design or contract work
- update `docs/_meta/documents.yaml` whenever a tracked doc is created, moved, replaced, or retired

## 5. How To Work On A Task

When implementing a feature or fix:

1. Read `docs/planning/STATUS.md` to confirm the active phase.
2. Read the active backlog doc under `docs/planning/`.
3. Read the active implementation order doc under `docs/planning/` when sequencing matters.
4. Inspect the affected code and tests before changing anything.
5. Implement the smallest cohesive unit that moves the task forward.
6. Add or update tests.
7. Run `powershell -ExecutionPolicy Bypass -File .\scripts\test.ps1`
8. Run `powershell -ExecutionPolicy Bypass -File .\scripts\lint.ps1`
9. Update docs when behavior, contracts, or operator workflow change.

## 6. Coding Rules

- use type hints everywhere
- keep functions small when practical
- prefer composition over inheritance
- keep route handlers thin
- keep service boundaries explicit

Naming:
- `snake_case` for functions and variables
- `PascalCase` for classes

## 7. Codex Integration Rules

Use `CodexBridge` for all Codex interactions.

Do not:
- call Codex directly from API routes
- duplicate Codex bridge logic in other modules

Use these primitives where relevant:
- `thread/start`
- `thread/resume`
- `turn/start`
- `turn/steer`
- `turn/interrupt`

## 8. Session And Agent Rules

- session is the main coordination unit
- agents communicate through coordinator-managed messages
- mentions trigger routing
- loop protection must remain in place

Rules:
- only the allowed initiator should trigger relay flows
- do not create direct agent-to-agent shortcuts that bypass coordinator logic
- keep transcript, artifact, and audit behavior consistent with current coordinator flow

## 9. Commands Behavior

Supported commands include:
- `/new` -> create session
- `/interrupt` -> stop the current turn
- `/compact` -> reduce context

Ensure commands:
- are parsed before routing
- do not reach Codex directly as raw user input

## 10. Database Rules

Use the repository layer only.

Primary tables include:
- `sessions`
- `agents`
- `messages`
- `jobs`
- `artifacts`

Do not:
- bypass repositories for persistence writes
- scatter persistence rules across unrelated services

## 11. Testing And Completion

Before considering a task done:
- tests pass
- lint passes
- changed APIs and operator flows are reflected in docs
- new behavior has test coverage

Preferred commands:
- `powershell -ExecutionPolicy Bypass -File .\scripts\test.ps1`
- `powershell -ExecutionPolicy Bypass -File .\scripts\lint.ps1`

## 12. What Not To Do

- do not rewrite the architecture without an explicit request
- do not break existing APIs without updating contract docs and tests
- do not skip tests
- do not introduce large speculative refactors during a scoped task

## 13. When Unsure

If unclear:
- inspect the current code and active docs first
- prefer a small concrete plan over broad changes
- ask for clarification only when local context cannot resolve the ambiguity safely
