[CmdletBinding()]
param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$DatabaseUrl = $(if ([string]::IsNullOrWhiteSpace($env:DATABASE_URL)) {
            "sqlite:///./data/codex_coordinator.db"
        } else {
            $env:DATABASE_URL
        }),
    [int]$StartupTimeoutSec = 60,
    [switch]$IncludeRelay
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

$env:DATABASE_URL = $DatabaseUrl

function New-ReleaseDatabaseUrl {
    param([string]$Prefix)
    $tempRoot = [System.IO.Path]::GetTempPath()
    $fileName = "{0}-{1}.db" -f $Prefix, ([guid]::NewGuid().ToString("N"))
    return Join-Path $tempRoot $fileName
}

Write-Host "Running test suite..."
& (Join-Path $PSScriptRoot "test.ps1")

Write-Host "Running lint checks..."
& (Join-Path $PSScriptRoot "lint.ps1")

$migrationDatabase = $null
$seedDatabase = $null

try {
    Write-Host "Verifying migration idempotency..."
    $migrationDatabase = New-ReleaseDatabaseUrl -Prefix "codex-release-migrations"
    & python -m app.services.release_readiness --database-url $migrationDatabase --check migrations

    Write-Host "Verifying demo seed reset..."
    $seedDatabase = New-ReleaseDatabaseUrl -Prefix "codex-release-seed"
    & python -m app.services.release_readiness --database-url $seedDatabase --check seed

    Write-Host "Running smoke checks..."
    $env:DATABASE_URL = $DatabaseUrl
    $env:APP_ENV = "production"
    $env:DEPLOYMENT_PROFILE = "small-team"
    if ($IncludeRelay) {
        & (Join-Path $PSScriptRoot "smoke.ps1") -BaseUrl $BaseUrl -DatabaseUrl $DatabaseUrl -StartupTimeoutSec $StartupTimeoutSec -IncludeRelay
    } else {
        & (Join-Path $PSScriptRoot "smoke.ps1") -BaseUrl $BaseUrl -DatabaseUrl $DatabaseUrl -StartupTimeoutSec $StartupTimeoutSec
    }

    Write-Host "Building release package..."
    & (Join-Path $PSScriptRoot "package_release.ps1") -OutputDir (Join-Path "dist" "release") -DeploymentProfile "small-team"
} finally {
    foreach ($path in @($migrationDatabase, $seedDatabase)) {
        if (-not [string]::IsNullOrWhiteSpace($path)) {
            Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Host "Release readiness checks passed."
