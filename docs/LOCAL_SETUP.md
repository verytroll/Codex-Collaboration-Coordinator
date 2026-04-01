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
and the smoke gate. It expects the local app to be reachable for the smoke step.

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
- `GET /.well-known/agent-card.json`
- `GET /api/v1/sessions`
- `GET /api/v1/jobs/{job_id}`
