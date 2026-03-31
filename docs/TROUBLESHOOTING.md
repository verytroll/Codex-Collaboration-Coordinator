# Troubleshooting

## Database problems

- If the app cannot open SQLite, confirm `DATABASE_URL` points at a writable local path.
- If the schema looks stale, delete the local `.db` file and run `.\scripts\seed.ps1` again.
- If migrations fail on startup, run `python -m pytest tests/integration/test_migrations.py` to confirm the schema runner still works.

## CodexBridge problems

- If relay work stalls, check that `codex app-server` is available in `PATH`.
- If you are running tests, the bridge is usually mocked. A missing Codex binary should not block the test suite.

## Streaming problems

- SSE endpoints return `text/event-stream`.
- If a client disconnects immediately, verify the client keeps the HTTP connection open.

## Presence and recovery

- Presence is driven by `POST /api/v1/agents/{agent_id}/heartbeat`.
- Restart recovery rehydrates thread mapping from persisted jobs. If a mapping looks missing, inspect the latest job row and runtime rows.

## General checks

```powershell
.\scripts\lint.ps1
.\scripts\test.ps1
```
