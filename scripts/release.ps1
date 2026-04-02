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

function Reset-TestEnvironment {
    $names = @(
        "APP_ENV",
        "DEPLOYMENT_PROFILE",
        "APP_HOST",
        "APP_PORT",
        "APP_RELOAD",
        "ACCESS_BOUNDARY_MODE",
        "CODEX_BRIDGE_MODE",
        "ACCESS_TOKEN",
        "ACCESS_TOKEN_HEADER",
        "ACTOR_ID",
        "ACTOR_ROLE",
        "ACTOR_TYPE",
        "ACTOR_LABEL",
        "RUNTIME_RECOVERY_ENABLED",
        "RUNTIME_RECOVERY_INTERVAL_SECONDS",
        "RUNTIME_STALE_AFTER_MINUTES"
    )

    foreach ($name in $names) {
        Remove-Item -Path "Env:$name" -ErrorAction SilentlyContinue
    }
}

function Start-ReleaseApp {
    param(
        [string]$AppHost,
        [string]$AppPort
    )

    $appRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
    $stdoutLog = Join-Path ([System.IO.Path]::GetTempPath()) ("codex-release-app-{0}.stdout.log" -f ([guid]::NewGuid().ToString("N")))
    $stderrLog = Join-Path ([System.IO.Path]::GetTempPath()) ("codex-release-app-{0}.stderr.log" -f ([guid]::NewGuid().ToString("N")))
    $process = Start-Process `
        -FilePath "python" `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", $AppHost, "--port", $AppPort) `
        -WorkingDirectory $appRoot `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -PassThru
    return [pscustomobject]@{
        process = $process
        stdout_log = $stdoutLog
        stderr_log = $stderrLog
    }
}

function Stop-ReleaseApp {
    param([object]$AppProcess)

    if ($null -eq $AppProcess -or $null -eq $AppProcess.process) {
        return
    }

    try {
        if (-not $AppProcess.process.HasExited) {
            Stop-Process -Id $AppProcess.process.Id -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        }
    } catch {
        # Ignore shutdown races; the release script is already handling failure paths.
    }
}

Reset-TestEnvironment

$migrationDatabase = $null
$seedDatabase = $null
$appProcess = $null

try {
    Write-Host "Running test suite..."
    & (Join-Path $PSScriptRoot "test.ps1")

    Write-Host "Running lint checks..."
    & (Join-Path $PSScriptRoot "lint.ps1")

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
    $env:APP_HOST = "127.0.0.1"
    $env:APP_PORT = "8000"
    $env:APP_RELOAD = "false"
    $appProcess = Start-ReleaseApp -AppHost $env:APP_HOST -AppPort $env:APP_PORT
    if ($IncludeRelay) {
        & (Join-Path $PSScriptRoot "smoke.ps1") -BaseUrl $BaseUrl -DatabaseUrl $DatabaseUrl -StartupTimeoutSec $StartupTimeoutSec -IncludeRelay
    } else {
        & (Join-Path $PSScriptRoot "smoke.ps1") -BaseUrl $BaseUrl -DatabaseUrl $DatabaseUrl -StartupTimeoutSec $StartupTimeoutSec
    }

    Stop-ReleaseApp -AppProcess $appProcess

    Write-Host "Building release package..."
    & (Join-Path $PSScriptRoot "package_release.ps1") -OutputDir (Join-Path "dist" "release") -DeploymentProfile "small-team"
} finally {
    Stop-ReleaseApp -AppProcess $appProcess
    foreach ($path in @($migrationDatabase, $seedDatabase)) {
        if (-not [string]::IsNullOrWhiteSpace($path)) {
            Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Host "Release readiness checks passed."
