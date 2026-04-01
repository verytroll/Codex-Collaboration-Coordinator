# Operator UI Shell

The operator UI shell is a thin read-only surface for the coordinator.

## Routes

- `GET /operator`
- `GET /api/v1/operator/shell`
- `GET /api/v1/operator/sessions/{session_id}/activity`

## What the shell shows

- sessions
- participants
- transcript messages
- jobs
- approvals
- artifacts
- transcript exports
- dashboard summaries for bottlenecks, phases, and runtime pools
- replayable session activity, including messages, jobs, reviews, approvals, and runtime health signals

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

## Live activity

The activity endpoint returns a replayable window for a single session.

- `since_sequence=0` returns the most recent window for the session
- `since_sequence=<cursor>` returns only events after that cursor
- `next_cursor_sequence` is the cursor you should pass on the next poll
- the feed includes signals for pending approvals, recent errors, stuck jobs, phase bottlenecks, and runtime health abnormalities

The shell uses that contract for its live activity panel and polls it while live mode is enabled.

## Access boundary

- `ACCESS_BOUNDARY_MODE=local` and `trusted` allow the shell without a token.
- `ACCESS_BOUNDARY_MODE=protected` requires `ACCESS_TOKEN`.
- The shell page injects the configured token into its fetch layer when the page is rendered in protected mode.

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
