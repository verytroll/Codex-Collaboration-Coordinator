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
$BaseUrl = $BaseUrl.TrimEnd("/")

function Invoke-ApiGet {
    param([string]$Path)
    Invoke-RestMethod -Method Get -Uri "$BaseUrl$Path" -TimeoutSec 30
}

function Invoke-ApiPost {
    param(
        [string]$Path,
        [object]$Body
    )
    $payload = if ($Body -is [string]) {
        $Body
    } else {
        $Body | ConvertTo-Json -Depth 10
    }
    Invoke-RestMethod -Method Post -Uri "$BaseUrl$Path" -ContentType "application/json" -Body $payload -TimeoutSec 30
}

function Assert-Condition {
    param(
        [bool]$Condition,
        [string]$Message
    )
    if (-not $Condition) {
        throw $Message
    }
}

function Wait-ForServer {
    param(
        [string]$Path,
        [int]$TimeoutSec
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            return Invoke-ApiGet $Path
        } catch {
            if ($_.Exception.Response) {
                throw
            }
            Start-Sleep -Seconds 1
        }
    }

    throw "Server at $BaseUrl did not become ready within $TimeoutSec seconds. Start the app with .\scripts\dev.ps1 and try again."
}

Write-Host "Checking health endpoints..."
$health = Wait-ForServer -Path "/api/v1/healthz" -TimeoutSec $StartupTimeoutSec
Assert-Condition ($health.status -eq "ok") "healthz did not return ok"

$agentCard = Invoke-ApiGet "/.well-known/agent-card.json"
Assert-Condition ($agentCard.capabilities.streaming -eq $true) "agent-card streaming capability missing"
Assert-Condition ($agentCard.capabilities.push_notifications -eq $false) "agent-card push_notifications should be false"

Write-Host "Seeding demo data..."
& (Join-Path $PSScriptRoot "seed.ps1")

Write-Host "Checking seeded objects..."
$agents = Invoke-ApiGet "/api/v1/agents"
$sessions = Invoke-ApiGet "/api/v1/sessions"
Assert-Condition (@($agents.agents | Where-Object { $_.id -eq "agt_builder_demo" }).Count -ge 1) "builder demo agent missing"
Assert-Condition (@($sessions.sessions | Where-Object { $_.id -eq "ses_demo" }).Count -ge 1) "demo session missing"

Write-Host "Posting a normal message..."
$messageResponse = Invoke-ApiPost "/api/v1/sessions/ses_demo/messages" @{
    sender_type       = "agent"
    sender_id         = "agt_builder_demo"
    content           = "hello from smoke"
    reply_to_message_id = $null
}
Assert-Condition (@($messageResponse.routing.created_jobs).Count -eq 0) "plain message should not create jobs"

$messages = Invoke-ApiGet "/api/v1/sessions/ses_demo/messages"
Assert-Condition (@($messages.messages).Count -ge 1) "expected at least one session message"

if ($IncludeRelay) {
    Write-Host "Posting a mention message to exercise relay..."
    $relayResponse = Invoke-ApiPost "/api/v1/sessions/ses_demo/messages" @{
        sender_type       = "agent"
        sender_id         = "agt_builder_demo"
        content           = "#builder smoke relay"
        reply_to_message_id = $null
    }
    Assert-Condition (@($relayResponse.routing.created_jobs).Count -ge 1) "mention message should create at least one job"
    $jobId = @($relayResponse.routing.created_jobs)[0]
    $job = Invoke-ApiGet "/api/v1/jobs/$jobId"
    Assert-Condition ($job.job.job.id -eq $jobId) "job detail endpoint returned the wrong job"
}

Write-Host "Smoke checks passed."
