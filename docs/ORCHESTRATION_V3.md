# Orchestration V3

F28 introduces a minimal orchestration state model and gated phase transitions on top of the
existing review and approval flows.

## State model

`orchestration_runs` stores one active run per session with:

- `current_phase_key`
- `pending_phase_key`
- `failure_phase_key`
- `gate_type`
- `gate_status`
- links to `source_job_id`, `handoff_job_id`, `review_id`, `approval_id`
- links to transition and decision artifacts

The run is the source of truth for whether a session is:

- `active`
- `blocked`
- `completed`

## Public API

- `POST /api/v1/orchestration/sessions/{session_id}/start`
- `GET /api/v1/orchestration/sessions/{session_id}`
- `GET /api/v1/orchestration/runs`
- `POST /api/v1/orchestration/sessions/{session_id}/gate`

## Gate behavior

### `review_required`

- opens a review request for a source job
- creates a handoff job and a transition artifact
- on `approved`, the run advances to the success phase
- on `changes_requested`, the run moves to `revise`

### `approval_required`

- opens an approval request for a source job
- creates a handoff job and a transition artifact
- on `accepted`, the run advances to the success phase
- on `declined`, the run moves to `revise`

## Review and approval hooks

The existing review and approval API routes now call the orchestration gate service after the
underlying review/approval decision is persisted. That keeps the public surface stable while the
phase transition state stays consistent.
