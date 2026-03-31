$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

if ([string]::IsNullOrWhiteSpace($env:DATABASE_URL)) {
    $env:DATABASE_URL = "sqlite:///./codex_coordinator.db"
}

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
