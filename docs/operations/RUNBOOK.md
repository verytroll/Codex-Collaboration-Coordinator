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

4. Open `http://127.0.0.1:8000/operator` to inspect the thin operator shell and action panel.
5. If you are calling write routes directly in `protected` mode, include the actor
   identity headers (`X-Actor-Id`, `X-Actor-Role`, optionally `X-Actor-Type` and
   `X-Actor-Label`) along with the access token.

## Prod-like startup

1. Keep `DATABASE_URL` pointed at a writable local SQLite file.
2. Set `CODEX_BRIDGE_MODE=local` unless you are explicitly testing another bridge mode.
3. Use `DEPLOYMENT_PROFILE=small-team` for the packaged deployment path, or
   `local-dev` / `trusted-demo` when you want a development or demo profile.
4. Set `ACCESS_BOUNDARY_MODE=trusted` for the default external-safety baseline, or
   `protected` with `ACCESS_TOKEN` when you want operator/public routes locked down.
5. Run the app with `.\scripts\run.ps1` or your preferred ASGI host command.
6. Confirm `GET /api/v1/healthz` returns `{"status":"ok"}`.
7. Confirm `GET /api/v1/readinessz` returns a ready response with `checks.db.status=ok`
   and `checks.migrations.status=ok`.
8. Confirm `GET /api/v1/system/status` reports the expected aggregates and bridge state.
9. Confirm `GET /operator` renders the operator shell and `GET /api/v1/operator/shell`
   returns the bootstrap payload for a selected session.
10. Confirm the operator action routes work for retry, resume, cancel, approve, reject,
    and phase activation, and that the session event log records the matching audit trail.
11. Confirm protected direct clients send actor identity headers, or rely on the shell's
    rendered defaults when using the operator UI page.
12. Confirm the operator live activity panel can reconnect through
    `/api/v1/operator/sessions/{session_id}/activity/stream` when the browser supports
    EventSource, and falls back to polling when it cannot send the configured access token.
13. In the packaged `small-team` path, confirm `RUNTIME_RECOVERY_ENABLED=true` so queued
    jobs can be replayed after restart.
14. For external A2A adoption, treat `docs/integrations/a2a/A2A_COMPATIBILITY_MATRIX.md` as the source of
    truth and use `scripts/a2a_quickstart.ps1` to exercise only the supported public v1
    surface.

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
5. smoke validation against the running app using the `small-team` deployment profile
6. release packaging into `dist/release`

Before considering the baseline closed, confirm:

1. The release package name includes the version and profile, for example
   `codex-collaboration-coordinator-0.3.0-small-team`.
2. `release-manifest.json` exists and records `app_version`, `release.tag`,
   `release.candidate`, and `deployment_profile=small-team`.
3. `profiles/small-team.env` exists in the bundle and matches the canonical small-team
   defaults, including durable runtime recovery settings.
4. The smoke path covers health, readiness, operator shell bootstrap, operator actions,
   live activity, and the public A2A flow.

## Incident triage

1. Check `GET /api/v1/system/status` first.
2. Check `GET /api/v1/system/debug` for queued jobs, blocked jobs, and runtime state.
3. Check `GET /api/v1/operator/dashboard` for higher-level operator diagnostics.
4. Check `GET /operator` if you want the shell view instead of raw JSON.
5. If operator/public routes return `401`, verify `ACCESS_TOKEN` and the request header name.
6. If operator/public routes return `403`, verify the token value being sent.
7. If a protected write route returns `401` with a valid token, check the actor identity
   headers first.
8. If a protected write route returns `403`, verify the actor role is allowed for the
   requested action.
9. Correlate logs by `request_id` from the request headers or the request log.
10. If the bridge is degraded, check the latest `bridge` samples in telemetry and restart the app after confirming the Codex binary is available.

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

