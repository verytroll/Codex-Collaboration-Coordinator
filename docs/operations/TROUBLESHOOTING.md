# Troubleshooting

## Database problems

- If the app cannot open SQLite, confirm `DATABASE_URL` points at a writable local path.
- If the schema looks stale, delete the local `.db` file and run `.\scripts\seed.ps1` again.
- If migrations fail on startup, run `python -m pytest tests/integration/test_migrations.py` to confirm the schema runner still works.
- If `scripts\release.ps1` fails with a migration checksum mismatch, do not edit the existing
  SQL file in place. Restore the old migration, add a new migration file, and rerun against a
  fresh SQLite database.
- If `GET /api/v1/readinessz` returns `503`, check whether the database path is writable and
  whether the migration table matches the bundled SQL files.

## CodexBridge problems

- If relay work stalls, check that `codex app-server` is available in `PATH`.
- If you are running tests, the bridge is usually mocked. A missing Codex binary should not block the test suite.
- If `codex app-server` cannot start, the process manager now surfaces a startup error instead of hanging silently.
- If an interrupt or retry request is replayed, the services should no-op instead of creating duplicate side effects.

## Streaming problems

- SSE endpoints return `text/event-stream`.
- If a client disconnects immediately, verify the client keeps the HTTP connection open.
- If the operator shell falls back to polling, check whether the browser can use EventSource
  without the configured access token headers.
- If reconnects keep resuming from the wrong point, inspect the `Last-Event-ID` header and the
  `since_sequence` query parameter on the stream request.

## A2A problems

- Use `docs/integrations/a2a/A2A_COMPATIBILITY_MATRIX.md` as the source of truth for supported versus experimental claims.
- If `/.well-known/agent-card.json` or `/api/v1/a2a/*` returns `401` or `403`, check `ACCESS_BOUNDARY_MODE` and whether `ACCESS_TOKEN` is set correctly.
- If `POST /api/v1/a2a/tasks` returns a task but the event list is empty, confirm the job was refreshed after the last state change.
- If `GET /api/v1/a2a/tasks/{task_id}/events?since_sequence=0` returns only `created`, create or update the underlying job or artifact before calling the route again.
- If the subscription SSE endpoint returns no frames, make sure the subscription cursor points at the same task and that the request is not filtered by a newer `since_sequence`.
- If `GET /api/v1/a2a/tasks/{task_id}/stream` keeps replaying from the beginning, confirm the client is sending the last seen cursor or `Last-Event-ID`.
- If a client depends on `/api/v1/a2a/jobs/{job_id}/project` or `/api/v1/a2a/sessions/{session_id}/tasks`, treat that as legacy compatibility, not the supported external contract.
- If the public A2A surface looks stale, re-run `.\scripts\a2a_quickstart.ps1` or `.\scripts\smoke.ps1` to confirm the public contract still replays correctly.

## Presence and recovery

- Presence is driven by `POST /api/v1/agents/{agent_id}/heartbeat`.
- Restart recovery rehydrates thread mapping from persisted jobs. If a mapping looks missing, inspect the latest job row and runtime rows.
- The durable runtime supervisor also replays queued jobs on startup in the packaged
  `small-team` path. That path enables runtime recovery through the profile defaults.
  If work stays queued after a restart, confirm the runtime is marked `online` or `busy`,
  that the bridge is available, and that no override disabled the packaged recovery
  settings.
- If a gate request is already pending for a session, repeat the same request rather than creating a new one. A mismatched request now fails with a conflict instead of overwriting the pending run.

## Reliability checks

- If `POST /api/v1/jobs/{job_id}/retry` or `/resume` is called twice in a row, only the first call should enqueue input.
- If `POST /api/v1/reviews/{review_id}/decision` is replayed with the same decision, it should return the existing review state.
- If runtime pool metadata is malformed in an old database snapshot, diagnostics should still render with safe defaults.
- If `scripts\release.ps1` reports that demo seed reset verification failed, remove the local
  SQLite file and rerun the release checklist. The demo seed should be stable across repeats.

## Telemetry checks

- If `telemetry.summary.queue_depth` stays high while `runtime_pool_pressure` is low, the bottleneck is likely upstream in job or review flow.
- If `bridge.error_rate` climbs, check the recent `codex_bridge` samples in `telemetry.latest` and `telemetry.recent_samples`.
- If the request log has the wrong `request_id`, verify the client sent `X-Request-ID` and the middleware is still mounted.

## General checks

```powershell
.\scripts\lint.ps1
.\scripts\test.ps1
.\scripts\smoke.ps1
```

If `smoke.ps1` reports that it cannot connect to the server, make sure `.\scripts\dev.ps1`
is running in another terminal and let it finish startup. The smoke script waits up to
60 seconds for the health endpoint before failing.

If `Dockerfile` builds successfully but the container fails readiness, inspect the mounted
SQLite volume and confirm the container can write the database file at startup.

