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
