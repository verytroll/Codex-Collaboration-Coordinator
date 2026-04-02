# Operator UI Shell

The operator UI shell is a thin operator surface for the coordinator.

## Routes

- `GET /operator`
- `GET /api/v1/operator/shell`
- `GET /api/v1/operator/sessions/{session_id}/activity`
- `GET /api/v1/operator/sessions/{session_id}/activity/stream`
- `POST /api/v1/operator/jobs/{job_id}/retry`
- `POST /api/v1/operator/jobs/{job_id}/resume`
- `POST /api/v1/operator/jobs/{job_id}/cancel`
- `POST /api/v1/operator/approvals/{approval_id}/approve`
- `POST /api/v1/operator/approvals/{approval_id}/reject`
- `POST /api/v1/operator/sessions/{session_id}/phases/{phase_key}/activate`

## What the shell shows

- sessions
- participants
- transcript messages
- jobs
- approvals
- artifacts
- transcript exports
- dashboard summaries for bottlenecks, phases, and runtime pools
- replayable session activity, including messages, jobs, reviews, approvals, runtime health signals, and operator write actions
- a compact incident summary for the selected session, derived from the replayable activity and signal feed

## Filters

The backend bootstrap endpoint accepts these dashboard filters:

- `session_id`
- `template_key`
- `phase_key`
- `runtime_pool_key`

The page also keeps local presentation filters for:

- session search
- session status
- approval state

Those local filters do not change backend orchestration state. They only change what the shell renders.

The shell also includes an operator action panel for:

- phase activation
- job retry, resume, and cancel
- approval approve and reject

Each write action asks for a confirmation step and records a session audit event with actor, target, reason, and result.

The shell renders actor identity defaults into its fetch layer so protected mode writes
send the configured `X-Actor-*` headers automatically. Direct API clients should use the
same header names when they call the operator or approval routes.

## Live activity

The activity endpoint returns a replayable window for a single session.

- `since_sequence=0` returns the most recent window for the session
- `since_sequence=<cursor>` returns only events after that cursor
- `next_cursor_sequence` is the cursor you should pass on the next poll
- the feed includes signals for pending approvals, recent errors, stuck jobs, phase bottlenecks, and runtime health abnormalities
- the shell groups replayable activity by category so incident reading is easier during triage
- the stream route uses SSE with `Last-Event-ID` / `since_sequence` resume support
- the shell prefers SSE in local/trusted modes and falls back to polling when EventSource cannot send the configured access token headers

The shell uses that contract for its live activity panel and keeps the cursor in sync whether it is polling or streaming.

## Access boundary

- `ACCESS_BOUNDARY_MODE=local` and `trusted` allow the shell without a token.
- `ACCESS_BOUNDARY_MODE=protected` requires `ACCESS_TOKEN`.
- The shell page injects the configured token into its fetch layer when the page is rendered in protected mode.
- In protected mode, the shell also injects the configured actor identity headers so
  operator and approval actions satisfy the RBAC checks.

## Local use

1. Start the app with `.\scripts\dev.ps1`
2. Open `http://127.0.0.1:8000/operator`
3. Pick a session from the left rail
4. Refresh to re-read backend state

## Smoke coverage

`.\scripts\smoke.ps1` now checks:

- the shell page loads and includes the main UI anchors
- the bootstrap endpoint returns a selected session
- transcript, jobs, approvals, and artifacts are present for the seeded session
- the realtime activity endpoint returns replayable events and signals for the seeded session
- the operator action panel is rendered with the expected action anchors
