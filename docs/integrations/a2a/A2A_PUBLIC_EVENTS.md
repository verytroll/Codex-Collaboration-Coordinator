# A2A Public Events

This document describes the supported public subscribe/push event surface for A2A tasks.
For the claim boundary and adoption baseline, see `docs/integrations/a2a/A2A_COMPATIBILITY_MATRIX.md`.

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
- `GET /api/v1/a2a/tasks/{task_id}/stream`
- `GET /api/v1/a2a/subscriptions/{subscription_id}/events`
- `POST /api/v1/operator/a2a/tasks/{task_id}/webhooks`
- `GET /api/v1/operator/a2a/tasks/{task_id}/webhooks`
- `GET /api/v1/operator/a2a/tasks/{task_id}/webhook-deliveries`
- `POST /api/v1/operator/a2a/tasks/webhooks/{registration_id}/disable`

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

The direct stream envelope includes:

- `api_version: "v1"`
- `contract_version: "a2a.public.task.event.stream.v1"`
- `task_id`
- `since_sequence`
- `next_cursor_sequence`
- `delivery_mode: "sse"`
- `generated_at`
- `events`

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
- `GET /api/v1/a2a/tasks/{task_id}/stream` returns SSE frames for direct task streaming.
- `GET /api/v1/a2a/subscriptions/{subscription_id}/events` returns SSE frames.
- Replay is ordered by `sequence`.
- The cursor is inclusive by request and exclusive in the stored event log, so clients can resume from the last seen `sequence`.
- SSE reconnects can reuse `Last-Event-ID` or `since_sequence` to resume from the latest cursor.

## Event payload

Each event includes:

- public task snapshot
- event type
- sequence number
- minimal change metadata

The event payload excludes coordinator-internal state such as raw Codex bridge details.

## Managed outbound webhooks

Webhook delivery reuses the same public event payload contract instead of defining a second
event model.

- Registrations are operator-managed and scoped to a single public `task_id`.
- Delivery is `at-least-once`; receivers must treat `event_id` or `sequence` as idempotency keys.
- Ordering is preserved per registration by `event_sequence`.
- The coordinator signs the raw JSON body with `HMAC-SHA256` and sends:
  - `X-CCC-Event-Id`
  - `X-CCC-Event-Sequence`
  - `X-CCC-Task-Id`
  - `X-CCC-Delivery-Attempt`
  - `X-CCC-Signature`
- `2xx` responses mark a delivery successful.
- Non-`2xx` responses and transport errors are retried through the durable outbound delivery log.
- Disabled registrations stop enqueuing new deliveries; existing rows remain visible through
  the operator delivery listing.

## Notes

- The event log is persisted in SQLite.
- Managed outbound webhook registrations and deliveries are also persisted in SQLite.
- The public task projection remains the source of truth.
- Event replay is intentionally minimal but supported for client polling and SSE consumption.
- The direct stream route is useful when a client already has a replay cursor and wants to stay on SSE instead of polling.
- For a public client demo and example cursor flow, see `docs/integrations/a2a/A2A_QUICKSTART.md`.

