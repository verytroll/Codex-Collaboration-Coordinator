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
| Managed outbound webhooks | Supported | `POST /api/v1/operator/a2a/tasks/{task_id}/webhooks`, `GET /api/v1/operator/a2a/tasks/{task_id}/webhook-deliveries` |
| Managed integration credentials | Supported | `POST /api/v1/operator/integration-principals`, `POST /api/v1/operator/integration-principals/{principal_id}/credentials`, `Authorization: Bearer <secret>` |
| Public v1 contract markers | Supported | `a2a.public.task.v1`, `a2a.public.task.event.v1`, `a2a.public.task.subscription.v1`, `a2a.public.task.event.stream.v1` |
| Agent card contract | Supported | `a2a.agent-card.v1`, `/.well-known/agent-card.json` |
| Supported auth modes | Supported | `local`, `trusted`, `protected` deployment modes with managed credentials preferred for external clients |

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
2. A managed integration credential issued through the operator API and sent as `Authorization: Bearer <secret>`.
3. `POST /api/v1/a2a/tasks` to project a job into the public task contract.
4. `GET /api/v1/a2a/tasks/{task_id}/events` for JSON replay.
5. `GET /api/v1/a2a/tasks/{task_id}/stream` or `GET /api/v1/a2a/subscriptions/{subscription_id}/events` for SSE.
6. Operator-managed webhook registration only when push delivery is needed.

## Governance baseline

- Source of truth for supported versus experimental claims: this matrix.
- Source of truth for route and payload details: `docs/integrations/a2a/A2A_PUBLIC_API.md` and `docs/integrations/a2a/A2A_PUBLIC_EVENTS.md`.
- Source of truth for repeatable verification: `scripts/a2a_conformance.ps1` plus the integration contract tests.
- Supported baseline is the current documented release line only. Older release lines or compatibility routes are best-effort unless release notes explicitly say otherwise.

## Versioning and deprecation

- `/api/v1/a2a` is the supported route family for the early-adopter baseline.
- `api_version` and `contract_version` markers are the compatibility markers clients should pin to.
- Additive compatible changes and docs clarifications may land without a new contract marker when existing semantics remain intact.
- Breaking changes to payload shape, route semantics, cursor behavior, SSE resume behavior, or webhook header meaning require a new versioned contract marker and updated docs/tests.
- Legacy bridge routes stay available for compatibility only and are not part of the supported external contract.
- Any supported-surface deprecation must be reflected in docs, compatibility notes, and the conformance path before the claim changes.

Sample client flow:

- `scripts/a2a_quickstart.ps1`
- `scripts/a2a_conformance.ps1`

Contract tests:

- `tests/integration/test_a2a_contract.py`
- `tests/integration/test_public_contract.py`
- `tests/integration/test_a2a_conformance.py`

