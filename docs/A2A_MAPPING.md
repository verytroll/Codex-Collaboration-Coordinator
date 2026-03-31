# A2A Mapping Note

This repository remains coordinator-first. The A2A surface is a placeholder for discovery and future adapters.

## Internal to A2A mapping

- `session` maps to an A2A conversation or workspace scope.
- `job` maps to an A2A task.
- `job_events` map to task progress updates.
- `artifacts` map to task artifacts.
- `presence_heartbeats` map to runtime availability signals.
- `session_events` map to the session activity timeline.

## Status mapping

- `queued` maps to `submitted`
- `running` maps to `working`
- `input_required` maps to `input_required`
- `auth_required` maps to `auth_required`
- `completed` maps to `completed`
- `canceled` maps to `canceled`
- `failed` maps to `failed`
- `paused_by_loop_guard` maps to a guarded or paused internal state

## Placeholder agent card

The discovery endpoint at `/.well-known/agent-card.json` advertises:

- `streaming = true`
- `push_notifications = false`
- collaboration and Codex execution skills

## Design note

The coordinator API is not a public A2A implementation yet. Future A2A support should sit in an adapter layer, not replace the internal session/job model.
