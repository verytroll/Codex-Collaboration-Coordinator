# A2A Quickstart

This quickstart shows the supported public A2A task surface that external clients should use.
For the supported-versus-experimental claim boundary, see `docs/integrations/a2a/A2A_COMPATIBILITY_MATRIX.md`.

## 1. Start the app

```powershell
.\scripts\dev.ps1
```

If you are using protected mode, set `ACCESS_TOKEN` before calling any operator or A2A
route. For external clients, prefer a managed integration credential issued through the
operator API and send it as `Authorization: Bearer <secret>`.

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

The public task API projects an existing internal job into the external A2A shape. When
you use a managed credential, add `-H "Authorization: Bearer <secret>"` to the requests
below. Use `public_read` for replay/list access and `public_write` for task creation.

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

## 7. Register a managed outbound webhook

Use an operator token or `operator_write` credential to register a webhook for a projected
task:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/operator/a2a/tasks/task_123/webhooks `
  -H "Content-Type: application/json" `
  -H "X-Access-Token: <service-token>" `
  -d "{\"target_url\":\"http://127.0.0.1:9001/hook\",\"signing_secret\":\"replace-me\"}"
```

The response includes:

- `webhook.id`
- `webhook.status`
- `webhook.signing_secret_prefix`
- one-time `signing_secret` when you provide or generate the shared secret

Receivers should verify `X-CCC-Signature`, return `2xx` on success, and treat
`X-CCC-Event-Id` or `X-CCC-Event-Sequence` as idempotency keys.

## 8. Run the conformance verifier

Use the conformance script when you want a repeatable pass/fail check for the supported
early-adopter baseline instead of a guided demo:

```powershell
.\scripts\a2a_conformance.ps1
```

The verifier checks:

- discovery metadata and supported-versus-experimental notes
- managed integration credential issuance and bearer auth
- task projection, replay, subscription lookup, and SSE stream markers
- operator-managed outbound webhook registration and delivery signature semantics

## Compatibility notes

- Use `POST /api/v1/a2a/tasks` for refresh/project semantics.
- Use `GET /api/v1/a2a/tasks/{task_id}/events` for JSON replay.
- Use `GET /api/v1/a2a/subscriptions/{subscription_id}/events` for SSE consumption.
- Use the operator webhook routes only when you need push delivery; polling and SSE remain supported.
- The public task contract is `a2a.public.task.v1`.
- The event contract is `a2a.public.task.event.v1`.
- Managed integration credentials are the supported external auth path; the shared
  `ACCESS_TOKEN` remains a bootstrap and compatibility fallback.
- The quickstart only uses supported public v1 endpoints, not the legacy experimental bridge routes.
- Use `scripts/a2a_conformance.ps1` when you need evidence that a deployment still matches the supported matrix.

