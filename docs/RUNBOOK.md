# Runbook

## Local startup

1. Install the dev dependencies:

```powershell
pip install -e .[dev]
```

2. Start the coordinator with development defaults:

```powershell
.\scripts\dev.ps1
```

3. Verify the app is ready:

```powershell
.\scripts\smoke.ps1
```

4. Open `http://127.0.0.1:8000/operator` to inspect the thin operator shell.

## Prod-like startup

1. Keep `DATABASE_URL` pointed at a writable local SQLite file.
2. Set `CODEX_BRIDGE_MODE=local` unless you are explicitly testing another bridge mode.
3. Set `ACCESS_BOUNDARY_MODE=trusted` for the default external-safety baseline, or
   `protected` with `ACCESS_TOKEN` when you want operator/public routes locked down.
4. Run the app with `.\scripts\run.ps1` or your preferred ASGI host command.
5. Confirm `GET /api/v1/healthz` returns `{"status":"ok"}`.
6. Confirm `GET /api/v1/readinessz` returns a ready response with `checks.db.status=ok`
   and `checks.migrations.status=ok`.
7. Confirm `GET /api/v1/system/status` reports the expected aggregates and bridge state.
8. Confirm `GET /operator` renders the operator shell and `GET /api/v1/operator/shell`
   returns the bootstrap payload for a selected session.

## Release candidate

Run the repeatable release gate from a clean checkout:

```powershell
.\scripts\release.ps1
```

The release gate performs:

1. `pytest`
2. Ruff checks
3. migration checksum/idempotency verification
4. demo seed reset verification
5. smoke validation against the running app

## Incident triage

1. Check `GET /api/v1/system/status` first.
2. Check `GET /api/v1/system/debug` for queued jobs, blocked jobs, and runtime state.
3. Check `GET /api/v1/operator/dashboard` for higher-level operator diagnostics.
4. Check `GET /operator` if you want the read-only shell view instead of raw JSON.
5. If operator/public routes return `401`, verify `ACCESS_TOKEN` and the request header name.
6. If operator/public routes return `403`, verify the token value being sent.
7. Correlate logs by `request_id` from the request headers or the request log.
8. If the bridge is degraded, check the latest `bridge` samples in telemetry and restart the app after confirming the Codex binary is available.

## SQLite backup and restore

1. Stop the app.
2. Copy the SQLite file to a safe location.
3. Restore by replacing the database file with the backup copy.
4. Run `.\scripts\smoke.ps1` after restore to confirm the schema and seed state still load.

## Runtime or bridge recovery

1. Confirm whether the failure is isolated to the Codex bridge or the full coordinator.
2. If the bridge process stopped, restart the app so the bridge manager can recover the subprocess cleanly.
3. If a runtime is stuck or offline, inspect `/api/v1/system/debug` and `/api/v1/operator/dashboard`.
4. If the runtime state is inconsistent after a crash, rebuild the local database from backup and rerun the release checklist.
