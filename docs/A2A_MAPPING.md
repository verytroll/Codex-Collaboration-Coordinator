# A2A Mapping

This document describes the experimental A2A adapter bridge used by F24.
For the public v1 contract, see `docs/A2A_PUBLIC_API.md`.
For the companion public event surface, see `docs/A2A_PUBLIC_EVENTS.md`.

## Internal model

The coordinator keeps its native model:

- `session`
- `job`
- `artifact`

The A2A adapter does not replace that model. It only projects it into a task-shaped view for experimental interop.

## Mapping

| Internal field | A2A field |
|---|---|
| `session.id` | `context_id` |
| `job.id` | `job_id` |
| adapter task id | `task_id` |
| `job.status` | `status` |
| `job.title` | `title` |
| `job.result_summary` or `job.instructions` | `summary` |
| `job.assigned_agent_id` | `assigned_agent_id` |
| `artifact.id` | artifact item `id` |
| `artifact.artifact_type` | artifact item `artifact_type` |
| `artifact.file_name` | artifact item `file_name` |
| `artifact.mime_type` | artifact item `mime_type` |

## Status translation

The adapter uses a small translation layer:

- `queued` -> `queued`
- `running` -> `in_progress`
- `input_required` -> `blocked`
- `auth_required` -> `blocked`
- `paused_by_loop_guard` -> `blocked`
- `blocked` -> `blocked`
- `completed` -> `completed`
- `failed` -> `failed`
- `canceled` -> `canceled`

## Routes

Legacy experimental bridge routes:

- `POST /api/v1/a2a/jobs/{job_id}/project`
- `GET /api/v1/a2a/sessions/{session_id}/tasks`

Public v1 task routes:

- `POST /api/v1/a2a/tasks`
- `GET /api/v1/a2a/tasks`
- `GET /api/v1/a2a/tasks/{task_id}`

Public v1 event routes:

- `POST /api/v1/a2a/tasks/{task_id}/subscriptions`
- `GET /api/v1/a2a/tasks/{task_id}/events`
- `GET /api/v1/a2a/subscriptions/{subscription_id}`
- `GET /api/v1/a2a/subscriptions/{subscription_id}/events`

## Phase link

The adapter includes the current active phase metadata when a job is projected. That lets the task view stay aligned with the session phase presets.

## Public v1 mapping

The public A2A contract is the recommended external integration surface.

| Internal model | Public v1 field | Notes |
|---|---|---|
| `session.id` | `context_id`, `session_id` | Stable session identity |
| `job.id` | `job_id` | Primary task source |
| `job.status` | `status.internal_status`, `status.state` | Normalized for external clients |
| `job.result_summary` / `job.instructions` | `summary` | Summary fallback is stable |
| `job.error_code` / `job.error_message` | `error` | Only present on failed/canceled tasks |
| `artifact.*` | `artifacts[]` | Artifact list is replayed on task refresh |
| public task refresh | `events` | Projection changes are recorded as replayable events |

Compatibility notes:

- `POST /api/v1/a2a/tasks` is effectively a public refresh/project operation for an internal job.
- Event replay is cursor-based and ordered by sequence.
- Subscription streams use the same replayable event log underneath.

## Scope

This is intentionally experimental.

- It keeps the coordinator internal model unchanged.
- It stores a lightweight mapping table in SQLite.
- It does not claim production-grade A2A compatibility yet.
