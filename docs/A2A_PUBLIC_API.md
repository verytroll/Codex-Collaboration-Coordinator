# A2A Public API v1

This document describes the public A2A task surface built on top of the adapter bridge.

## Contract

The public task payload carries an explicit version marker:

- `api_version: "v1"`
- `contract_version: "a2a.public.task.v1"`

The coordinator internal model remains the source of truth. The public API only projects:

- `session`
- `job`
- `phase`
- `artifact`

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

- This API is public and stable for v1.
- The adapter bridge remains the implementation layer underneath.
- Legacy experimental routes still exist for compatibility, but the public contract should use the endpoints above.
- For task lifecycle push/replay details, see `docs/A2A_PUBLIC_EVENTS.md`.
- For a copy-paste setup flow and demo script, see `docs/A2A_QUICKSTART.md`.
