# Local Setup

## Prerequisites

- Python 3.11 or newer
- PowerShell on Windows
- A virtual environment for local work

## Install

```powershell
pip install -e .[dev]
```

## Configure

1. Copy `.env.example` to `.env` if you want to override defaults.
2. Keep `DATABASE_URL` pointed at a local SQLite file.
3. Leave `CODEX_BRIDGE_MODE=local` for the MVP flow.
4. Use `DEPLOYMENT_PROFILE=local-dev` for everyday development, `trusted-demo` for a
   local demo or reverse-proxy test, and `small-team` for a packaged deployment-like
   startup.
5. If you enable `protected`, set `ACCESS_TOKEN` and optionally `ACCESS_TOKEN_HEADER`
   (default: `X-Access-Token`).
6. Open the operator shell at `http://127.0.0.1:8000/operator` after the app starts.

## Run

```powershell
.\scripts\dev.ps1
```

`dev.ps1` applies migrations before starting uvicorn, so it works on a fresh SQLite file.

To run a quick end-to-end smoke check against the running app:

```powershell
.\scripts\smoke.ps1
```

Use `-IncludeRelay` if you want to try the CodexBridge mention flow too.
The smoke script waits up to 60 seconds for the app to become ready, so it can be
run while `dev.ps1` is still starting.

To run the full release-readiness checklist locally:

```powershell
.\scripts\release.ps1
```

`release.ps1` runs `pytest`, Ruff, migration verification, demo seed reset verification,
the smoke gate, and the release packager. It expects the local app to be reachable for
the smoke step and defaults to the small-team database path.
If `ACCESS_TOKEN` is set in the environment, the smoke script sends it automatically to
protected operator/public routes.

For a deployment-style startup, use `.\scripts\run.ps1`. That script binds to
`0.0.0.0` by default, selects the `small-team` deployment profile, and keeps reload
disabled unless you override `APP_RELOAD=true`.

## Seed demo data

```powershell
.\scripts\seed.ps1
```

## Verify

```powershell
.\scripts\test.ps1
.\scripts\lint.ps1
```

## Useful endpoints

- `GET /api/v1/healthz`
- `GET /api/v1/readinessz`
- `GET /.well-known/agent-card.json`
- `POST /api/v1/a2a/tasks`
- `GET /api/v1/a2a/tasks`
- `GET /api/v1/a2a/tasks/{task_id}/events`
- `GET /api/v1/a2a/subscriptions/{subscription_id}/events`
- `GET /operator`
- `GET /api/v1/operator/shell`
- `GET /api/v1/operator/sessions/{session_id}/activity`
- `GET /api/v1/sessions`
- `GET /api/v1/jobs/{job_id}`

For a guided public A2A demo, run `.\scripts\a2a_quickstart.ps1`.
