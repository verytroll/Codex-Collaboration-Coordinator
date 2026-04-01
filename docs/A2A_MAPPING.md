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

## Phase link

The adapter includes the current active phase metadata when a job is projected. That lets the task view stay aligned with the session phase presets.

## Scope

This is intentionally experimental.

- It keeps the coordinator internal model unchanged.
- It stores a lightweight mapping table in SQLite.
- It does not claim production-grade A2A compatibility yet.
