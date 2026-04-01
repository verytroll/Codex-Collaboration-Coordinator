# A2A Public Events

This document describes the public subscribe/push event surface for A2A tasks.

## Contract

The public event payload carries an explicit version marker:

- `api_version: "v1"`
- `contract_version: "a2a.public.task.event.v1"`

The subscription payload carries its own marker:

- `api_version: "v1"`
- `contract_version: "a2a.public.task.subscription.v1"`

## Endpoints

- `POST /api/v1/a2a/tasks/{task_id}/subscriptions`
- `GET /api/v1/a2a/subscriptions/{subscription_id}`
- `GET /api/v1/a2a/tasks/{task_id}/events`
- `GET /api/v1/a2a/subscriptions/{subscription_id}/events`

## Subscription model

A subscription stores a replay cursor for a public task.

Request payload:

```json
{
  "since_sequence": 0
}
```

The subscription response includes:

- `subscription_id`
- `task_id`
- `cursor_sequence`
- `delivery_mode`

## Event types

Supported task event types:

- `created`
- `status_changed`
- `artifact_attached`
- `phase_changed`
- `review_requested`
- `completed`

## Replay model

- `GET /api/v1/a2a/tasks/{task_id}/events?since_sequence=...` returns JSON replay.
- `GET /api/v1/a2a/subscriptions/{subscription_id}/events` returns SSE frames.
- Replay is ordered by `sequence`.
- The cursor is inclusive by request and exclusive in the stored event log, so clients can resume from the last seen `sequence`.

## Event payload

Each event includes:

- public task snapshot
- event type
- sequence number
- minimal change metadata

The event payload excludes coordinator-internal state such as raw Codex bridge details.

## Notes

- The event log is persisted in SQLite.
- The public task projection remains the source of truth.
- Event replay is intentionally minimal but stable enough for client polling and SSE consumption.
