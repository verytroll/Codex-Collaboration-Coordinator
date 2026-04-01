[CmdletBinding()]
param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$DatabaseUrl = $(if ([string]::IsNullOrWhiteSpace($env:DATABASE_URL)) {
            "sqlite:///./codex_coordinator.db"
        } else {
            $env:DATABASE_URL
        }),
    [int]$StartupTimeoutSec = 60
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

$env:DATABASE_URL = $DatabaseUrl
$BaseUrl = $BaseUrl.TrimEnd("/")

function Invoke-ApiGet {
    param([string]$Path)
    $headers = Get-AccessHeaders
    if ($headers.Count -gt 0) {
        Invoke-RestMethod -Method Get -Uri "$BaseUrl$Path" -Headers $headers -TimeoutSec 30
    } else {
        Invoke-RestMethod -Method Get -Uri "$BaseUrl$Path" -TimeoutSec 30
    }
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
    $headers = Get-AccessHeaders
    if ($headers.Count -gt 0) {
        Invoke-RestMethod -Method Post -Uri "$BaseUrl$Path" -Headers $headers -ContentType "application/json" -Body $payload -TimeoutSec 30
    } else {
        Invoke-RestMethod -Method Post -Uri "$BaseUrl$Path" -ContentType "application/json" -Body $payload -TimeoutSec 30
    }
}

function Get-AccessHeaders {
    if ([string]::IsNullOrWhiteSpace($env:ACCESS_TOKEN)) {
        return @{}
    }

    $headerName = if ([string]::IsNullOrWhiteSpace($env:ACCESS_TOKEN_HEADER)) {
            "X-Access-Token"
        } else {
            $env:ACCESS_TOKEN_HEADER
        }

    $headers = @{}
    if ($headerName -ieq "Authorization") {
        $headers["Authorization"] = "Bearer $($env:ACCESS_TOKEN)"
        return $headers
    }

    $headers[$headerName] = $env:ACCESS_TOKEN
    return $headers
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

    throw "Server at $BaseUrl did not become ready within $TimeoutSec seconds."
}

function Get-AgentIdByDisplayName {
    param(
        [object[]]$Items,
        [string]$DisplayName
    )
    $match = @($Items | Where-Object { $_.display_name -eq $DisplayName })[0]
    if ($null -eq $match) {
        return $null
    }
    return $match.id
}

Write-Host "Waiting for the app to become ready..."
Wait-ForServer -Path "/api/v1/healthz" -TimeoutSec $StartupTimeoutSec | Out-Null
Wait-ForServer -Path "/api/v1/readinessz" -TimeoutSec $StartupTimeoutSec | Out-Null

Write-Host "Seeding demo data..."
& (Join-Path $PSScriptRoot "seed.ps1")

Write-Host "Loading demo participants..."
$agents = Invoke-ApiGet "/api/v1/agents"
$plannerAgentId = Get-AgentIdByDisplayName -Items $agents.agents -DisplayName "Planner"
$builderAgentId = Get-AgentIdByDisplayName -Items $agents.agents -DisplayName "Builder"
Assert-Condition (-not [string]::IsNullOrWhiteSpace($plannerAgentId)) "Planner demo agent missing"
Assert-Condition (-not [string]::IsNullOrWhiteSpace($builderAgentId)) "Builder demo agent missing"

Write-Host "Creating a demo job through the session message surface..."
$commandResponse = Invoke-ApiPost "/api/v1/sessions/ses_demo/messages" @{
    sender_type          = "agent"
    sender_id            = $plannerAgentId
    content              = "/new #builder public a2a quickstart"
    reply_to_message_id  = $null
    channel_key          = "general"
}
Assert-Condition ($commandResponse.message.message_type -eq "command") "Quickstart command was not recorded as a command"
Assert-Condition (@($commandResponse.routing.created_jobs).Count -ge 1) "Quickstart command did not create a job"
$jobId = @($commandResponse.routing.created_jobs)[0]

Write-Host "Discovering the public A2A surface..."
$agentCard = Invoke-ApiGet "/.well-known/agent-card.json"
Assert-Condition ($agentCard.contract_version -eq "a2a.agent-card.v1") "agent-card contract version missing"
Assert-Condition (@($agentCard.endpoints | Where-Object { $_.name -eq "create_task" }).Count -ge 1) "agent-card missing task endpoint metadata"

Write-Host "Projecting the job into the public A2A surface..."
$taskEnvelope = Invoke-ApiPost "/api/v1/a2a/tasks" @{
    job_id = $jobId
}
Assert-Condition ($taskEnvelope.task.job_id -eq $jobId) "public A2A task returned the wrong job id"
Assert-Condition ($taskEnvelope.task.contract_version -eq "a2a.public.task.v1") "public A2A task contract missing"

Write-Host "Creating a replay cursor..."
$subscriptionEnvelope = Invoke-ApiPost "/api/v1/a2a/tasks/$($taskEnvelope.task.task_id)/subscriptions" @{
    since_sequence = 0
}
Assert-Condition ($subscriptionEnvelope.subscription.task_id -eq $taskEnvelope.task.task_id) "subscription returned the wrong task id"

Write-Host "Reading replayable events..."
$eventsEnvelope = Invoke-ApiGet "/api/v1/a2a/tasks/$($taskEnvelope.task.task_id)/events?since_sequence=0"
Assert-Condition (@($eventsEnvelope.events).Count -ge 1) "public A2A task events were empty"

Write-Host "Quickstart summary"
Write-Host ("  Agent card: " + $agentCard.public_api_base_url)
Write-Host ("  Task id: " + $taskEnvelope.task.task_id)
Write-Host ("  Subscription id: " + $subscriptionEnvelope.subscription.subscription_id)
Write-Host ("  Event count: " + @($eventsEnvelope.events).Count)
Write-Host "Done."
