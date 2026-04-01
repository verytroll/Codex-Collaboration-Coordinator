[CmdletBinding()]
param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$DatabaseUrl = $(if ([string]::IsNullOrWhiteSpace($env:DATABASE_URL)) {
            "sqlite:///./codex_coordinator.db"
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

function Invoke-CheckedScript {
    param([string]$Path, [string[]]$Arguments)
    & $Path @Arguments
}

function New-ReleaseDatabaseUrl {
    param([string]$Prefix)
    $tempRoot = [System.IO.Path]::GetTempPath()
    $fileName = "{0}-{1}.db" -f $Prefix, ([guid]::NewGuid().ToString("N"))
    return Join-Path $tempRoot $fileName
}

Write-Host "Running test suite..."
Invoke-CheckedScript (Join-Path $PSScriptRoot "test.ps1") @()

Write-Host "Running lint checks..."
Invoke-CheckedScript (Join-Path $PSScriptRoot "lint.ps1") @()

$migrationDatabase = $null
$seedDatabase = $null

try {
    Write-Host "Verifying migration idempotency..."
    $migrationDatabase = New-ReleaseDatabaseUrl -Prefix "codex-release-migrations"
    Invoke-CheckedScript "python" @(
        "-m",
        "app.services.release_readiness",
        "--database-url",
        $migrationDatabase,
        "--check",
        "migrations"
    )

    Write-Host "Verifying demo seed reset..."
    $seedDatabase = New-ReleaseDatabaseUrl -Prefix "codex-release-seed"
    Invoke-CheckedScript "python" @(
        "-m",
        "app.services.release_readiness",
        "--database-url",
        $seedDatabase,
        "--check",
        "seed"
    )

Write-Host "Running smoke checks..."
$env:DATABASE_URL = $DatabaseUrl
$env:APP_ENV = "production"
$smokeArgs = @(
    "-BaseUrl", $BaseUrl,
    "-DatabaseUrl", $DatabaseUrl,
        "-StartupTimeoutSec", $StartupTimeoutSec.ToString()
    )
    if ($IncludeRelay) {
        $smokeArgs += "-IncludeRelay"
    }
    Invoke-CheckedScript (Join-Path $PSScriptRoot "smoke.ps1") $smokeArgs
} finally {
    foreach ($path in @($migrationDatabase, $seedDatabase)) {
        if (-not [string]::IsNullOrWhiteSpace($path)) {
            Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Host "Release readiness checks passed."
