# Troubleshooting

## Database problems

- If the app cannot open SQLite, confirm `DATABASE_URL` points at a writable local path.
- If the schema looks stale, delete the local `.db` file and run `.\scripts\seed.ps1` again.
- If migrations fail on startup, run `python -m pytest tests/integration/test_migrations.py` to confirm the schema runner still works.

## CodexBridge problems

- If relay work stalls, check that `codex app-server` is available in `PATH`.
- If you are running tests, the bridge is usually mocked. A missing Codex binary should not block the test suite.
- If `codex app-server` cannot start, the process manager now surfaces a startup error instead of hanging silently.
- If an interrupt or retry request is replayed, the services should no-op instead of creating duplicate side effects.

## Streaming problems

- SSE endpoints return `text/event-stream`.
- If a client disconnects immediately, verify the client keeps the HTTP connection open.

## Presence and recovery

- Presence is driven by `POST /api/v1/agents/{agent_id}/heartbeat`.
- Restart recovery rehydrates thread mapping from persisted jobs. If a mapping looks missing, inspect the latest job row and runtime rows.
- If a gate request is already pending for a session, repeat the same request rather than creating a new one. A mismatched request now fails with a conflict instead of overwriting the pending run.

## Reliability checks

- If `POST /api/v1/jobs/{job_id}/retry` or `/resume` is called twice in a row, only the first call should enqueue input.
- If `POST /api/v1/reviews/{review_id}/decision` is replayed with the same decision, it should return the existing review state.
- If runtime pool metadata is malformed in an old database snapshot, diagnostics should still render with safe defaults.

## General checks

```powershell
.\scripts\lint.ps1
.\scripts\test.ps1
.\scripts\smoke.ps1
```

If `smoke.ps1` reports that it cannot connect to the server, make sure `.\scripts\dev.ps1`
is running in another terminal and let it finish startup. The smoke script waits up to
60 seconds for the health endpoint before failing.
