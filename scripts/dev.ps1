$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

if ([string]::IsNullOrWhiteSpace($env:DATABASE_URL)) {
    $env:DATABASE_URL = "sqlite:///./codex_coordinator.db"
}
if ([string]::IsNullOrWhiteSpace($env:APP_ENV)) {
    $env:APP_ENV = "development"
}
if ([string]::IsNullOrWhiteSpace($env:DEPLOYMENT_PROFILE)) {
    $env:DEPLOYMENT_PROFILE = "local-dev"
}
if ([string]::IsNullOrWhiteSpace($env:APP_HOST)) {
    $env:APP_HOST = "127.0.0.1"
}
if ([string]::IsNullOrWhiteSpace($env:APP_PORT)) {
    $env:APP_PORT = "8000"
}
if ([string]::IsNullOrWhiteSpace($env:APP_RELOAD)) {
    $env:APP_RELOAD = "true"
}

if ($env:APP_RELOAD.ToLowerInvariant() -eq "true") {
    python -m uvicorn app.main:app --reload --host $env:APP_HOST --port $env:APP_PORT
} else {
    python -m uvicorn app.main:app --host $env:APP_HOST --port $env:APP_PORT
}
