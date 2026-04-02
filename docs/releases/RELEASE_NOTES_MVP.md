# MVP Release Notes

## Release date

2026-03-31

## Included

- Session and agent CRUD
- Participant and message routing
- CodexBridge subprocess manager and JSON-RPC client
- Runtime tracking and session-thread mapping
- Mention parsing and job creation
- Relay execution, command handlers, presence, recovery, loop guard
- Artifact creation, approval flow, and SSE streaming
- Placeholder A2A discovery surface

## Validation

- `ruff check .`
- `pytest`

## Known limitations

- The A2A surface is discovery-only.
- Production-grade auth is not implemented.
- Streaming is snapshot-based, not a long-lived event subscription bus.

## Next phase

- Build a real A2A adapter if the project needs to expose the coordinator externally.
