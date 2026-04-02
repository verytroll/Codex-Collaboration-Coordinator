# A2A Public API v1

This document describes the supported public A2A task surface built on top of the adapter bridge.
For the exact supported-versus-experimental claim boundary, see `docs/integrations/a2a/A2A_COMPATIBILITY_MATRIX.md`.

## Contract

The public task payload carries an explicit version marker:

- `api_version: "v1"`
- `contract_version: "a2a.public.task.v1"`

The coordinator internal model remains the source of truth. The public API only projects:

- `session`
- `job`
- `phase`
- `artifact`

## Authentication

The public surface accepts managed integration credentials for external clients. The
legacy `ACCESS_TOKEN` path remains available for bootstrap and compatibility.

- Send the secret as `Authorization: Bearer <secret>` or the configured access-token
  header.
- `public_read` covers list, read, and replay endpoints.
- `public_write` is required for `POST /api/v1/a2a/tasks`.
- `operator_write` includes the public scopes, but operator routes are documented
  separately.

## Endpoints

- `POST /api/v1/a2a/tasks`
- `GET /api/v1/a2a/tasks`
- `GET /api/v1/a2a/tasks/{task_id}`

Optional query parameter for list:

- `session_id`

The public task surface now has a companion event surface:

- `POST /api/v1/a2a/tasks/{task_id}/subscriptions`
- `GET /api/v1/a2a/subscriptions/{subscription_id}`
- `GET /api/v1/a2a/tasks/{task_id}/events`
- `GET /api/v1/a2a/subscriptions/{subscription_id}/events`

## Create request

```json
{
  "job_id": "job_123"
}
```

The create route refreshes the public projection for an existing internal job.

## Public task shape

The public task resource is normalized into these sub-models:

- `task`
- `task_status`
- `task_artifact`
- `task_error`

Key mappings:

- `session.id` -> `context_id` and `session_id`
- `job.id` -> `job_id`
- internal task mapping id -> `task_id`
- `job.status` -> `task_status.state`
- `job.error_code` / `job.error_message` -> `task_error`
- `artifact.id` -> `task_artifact.id`
- `artifact.artifact_type` -> `task_artifact.artifact_type`

## Status mapping

- `queued` -> `queued`
- `running` -> `in_progress`
- `input_required` -> `blocked`
- `auth_required` -> `blocked`
- `paused_by_loop_guard` -> `blocked`
- `blocked` -> `blocked`
- `completed` -> `completed`
- `failed` -> `failed`
- `canceled` -> `canceled`

## Notes

- This API is the supported external v1 contract for public adoption.
- The adapter bridge remains the implementation layer underneath.
- Legacy experimental routes still exist for compatibility, but they are not part of the supported external contract.
- Managed integration credentials are the preferred auth path for external clients.
- For the full compatibility matrix, see `docs/integrations/a2a/A2A_COMPATIBILITY_MATRIX.md`.
- For task lifecycle push/replay details, see `docs/integrations/a2a/A2A_PUBLIC_EVENTS.md`.
- For a copy-paste setup flow and demo script, see `docs/integrations/a2a/A2A_QUICKSTART.md`.

