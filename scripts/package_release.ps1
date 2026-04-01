[CmdletBinding()]
param(
    [string]$SourceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$OutputDir = (Join-Path "dist" "release"),
    [string]$DeploymentProfile = $(if ([string]::IsNullOrWhiteSpace($env:DEPLOYMENT_PROFILE)) {
            "small-team"
        } else {
            $env:DEPLOYMENT_PROFILE
        })
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

python -m app.services.release_packaging --source-root $SourceRoot --output-dir $OutputDir --deployment-profile $DeploymentProfile
