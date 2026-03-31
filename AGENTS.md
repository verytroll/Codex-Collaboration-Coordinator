# AGENTS.md

## 1. Project Overview

This project is **Codex Collaboration Coordinator**.

It is a multi-agent coordination system that:
- manages sessions
- routes messages between agents
- integrates with Codex app-server
- supports mention-based collaboration (#agent)

Core architecture:
- Coordinator-first
- Codex is execution engine (via CodexBridge)
- Session + Agent + Message + Job model

---

## 2. Tech Stack

- Python 3.11+
- FastAPI (API layer)
- SQLite (MVP)
- Async (async/await required)

DO NOT:
- use Flask
- use blocking I/O
- introduce unnecessary frameworks

---

## 3. Project Structure

Follow this structure:

- app/
  - api/
  - services/
  - repositories/
  - models/
  - codex_bridge/
- tests/
- docs/

DO NOT:
- mix business logic inside API layer
- access DB directly from routes

---

## 4. Coding Rules

- Use type hints everywhere
- Use async functions for I/O
- Keep functions small (<50 lines)
- Prefer composition over inheritance

Naming:
- snake_case for functions
- PascalCase for classes

---

## 5. How to Work on a Task

When implementing a feature:

1. Read IMPLEMENTATION_TASKS.md
2. Follow IMPLEMENTATION_ORDER.md
3. Implement smallest working unit
4. Add tests
5. Run tests
6. Update docs

---

## 6. Testing

Always run:

pytest

Rules:
- Every new feature must have tests
- Fix failing tests before continuing
- Do not skip tests

---

## 7. Codex Integration Rules

Use CodexBridge for ALL Codex interactions.

DO NOT:
- call Codex directly from API
- duplicate Codex logic

Use:
- thread/start
- turn/start
- turn/steer
- turn/interrupt

---

## 8. Session & Agent Rules

- Session is the main coordination unit
- Agents communicate via messages
- Mentions (#agent_name) trigger routing

Rules:
- Only lead agent can initiate relay
- Prevent infinite loops (use loop guard)

---

## 9. Commands Behavior

Supported commands:
- /new → create session
- /interrupt → stop current turn
- /compact → reduce context

Ensure commands:
- are parsed before routing
- do not reach Codex directly

---

## 10. Database Rules

Use repository layer ONLY.

Tables:
- sessions
- agents
- messages
- jobs
- artifacts

DO NOT:
- write raw SQL in services
- bypass repository layer

---

## 11. PR Rules

Before completing a task:

- code compiles
- tests pass
- no lint errors

Commit format:

[MODULE] Short description

---

## 12. What NOT to Do

- Do not rewrite architecture
- Do not introduce new dependencies without reason
- Do not skip tests
- Do not break existing APIs

---

## 13. When Unsure

If unclear:
- ask for clarification
- propose a plan before coding
