[CmdletBinding()]
param(
    [string]$DatabaseUrl = $(if ([string]::IsNullOrWhiteSpace($env:DATABASE_URL)) {
            "sqlite:///./codex_coordinator.db"
        } else {
            $env:DATABASE_URL
        })
)

$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

python -m app.services.demo_seed --database-url $DatabaseUrl
