# A2A Quickstart

This quickstart shows the supported public A2A task surface that external clients should use.
For the supported-versus-experimental claim boundary, see `docs/A2A_COMPATIBILITY_MATRIX.md`.

## 1. Start the app

```powershell
.\scripts\dev.ps1
```

If you are using protected mode, set `ACCESS_TOKEN` before calling any operator or A2A route.

## 2. Inspect discovery metadata

```powershell
curl.exe http://127.0.0.1:8000/.well-known/agent-card.json
```

The agent card advertises:

- the public A2A base URL
- task and event endpoints
- supported capabilities
- compatibility notes

## 3. Create or refresh a public task

The public task API projects an existing internal job into the external A2A shape.

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/a2a/tasks `
  -H "Content-Type: application/json" `
  -d "{\"job_id\":\"job_123\"}"
```

The response contains:

- `task_id`
- `session_id`
- `job_id`
- normalized `status`
- normalized `artifacts`
- normalized `error` when applicable

## 4. Replay task events

```powershell
curl.exe "http://127.0.0.1:8000/api/v1/a2a/tasks/task_123/events?since_sequence=0"
```

Use `since_sequence=0` for the full replay window. The response includes:

- `events`
- `since_sequence`
- replayable `sequence` values

## 5. Create a subscription cursor

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/a2a/tasks/task_123/subscriptions `
  -H "Content-Type: application/json" `
  -d "{\"since_sequence\":0}"
```

The subscription response gives you a durable cursor for replay and SSE streaming.

## 6. Run the bundled example

```powershell
.\scripts\a2a_quickstart.ps1
```

The script seeds demo data, creates a demo job, projects it into the public A2A surface,
and prints the task id, subscription id, and event count.

## Compatibility notes

- Use `POST /api/v1/a2a/tasks` for refresh/project semantics.
- Use `GET /api/v1/a2a/tasks/{task_id}/events` for JSON replay.
- Use `GET /api/v1/a2a/subscriptions/{subscription_id}/events` for SSE consumption.
- The public task contract is `a2a.public.task.v1`.
- The event contract is `a2a.public.task.event.v1`.
- The quickstart only uses supported public v1 endpoints, not the legacy experimental bridge routes.
