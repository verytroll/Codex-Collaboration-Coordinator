# A2A Compatibility Matrix

This document defines the supported external adoption baseline for the public A2A surface.
It is intentionally narrower than the full internal coordinator model.

## Supported surface

| Surface | Status | Evidence |
|---|---|---|
| Discovery agent card | Supported | `/.well-known/agent-card.json`, `tests/integration/test_a2a_contract.py` |
| Public task create / refresh | Supported | `POST /api/v1/a2a/tasks` |
| Public task read / list | Supported | `GET /api/v1/a2a/tasks`, `GET /api/v1/a2a/tasks/{task_id}` |
| Public event replay | Supported | `GET /api/v1/a2a/tasks/{task_id}/events` |
| Public task subscriptions | Supported | `POST /api/v1/a2a/tasks/{task_id}/subscriptions`, `GET /api/v1/a2a/subscriptions/{subscription_id}` |
| Public SSE stream | Supported | `GET /api/v1/a2a/tasks/{task_id}/stream`, `GET /api/v1/a2a/subscriptions/{subscription_id}/events` |
| Public v1 contract markers | Supported | `a2a.public.task.v1`, `a2a.public.task.event.v1`, `a2a.public.task.subscription.v1`, `a2a.public.task.event.stream.v1` |
| Supported auth modes | Supported | `local`, `trusted`, `protected` deployment modes |

## Experimental compatibility

| Surface | Status | Notes |
|---|---|---|
| Legacy A2A job projection bridge | Experimental | `POST /api/v1/a2a/jobs/{job_id}/project` |
| Legacy A2A session task bridge | Experimental | `GET /api/v1/a2a/sessions/{session_id}/tasks` |

## Out of scope

| Surface | Status | Notes |
|---|---|---|
| WebSocket transport | Out of scope | SSE is the claimed realtime transport |
| Enterprise SSO / org hierarchy | Out of scope | RBAC remains team-oriented and header-based |
| Universal protocol translation | Out of scope | The repo projects into the public v1 contract only |
| Broader A2A marketplace claims | Out of scope | The adoption baseline is local-first and small-team focused |

## Adoption baseline

External clients should use:

1. `GET /.well-known/agent-card.json` for discovery.
2. `POST /api/v1/a2a/tasks` to project a job into the public task contract.
3. `GET /api/v1/a2a/tasks/{task_id}/events` for JSON replay.
4. `GET /api/v1/a2a/tasks/{task_id}/stream` or `GET /api/v1/a2a/subscriptions/{subscription_id}/events` for SSE.

Sample client flow:

- `scripts/a2a_quickstart.ps1`

Contract tests:

- `tests/integration/test_a2a_contract.py`
- `tests/integration/test_public_contract.py`

