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
    $headers = Get-AccessHeaders
    if ($headers.Count -gt 0) {
        Invoke-RestMethod -Method Get -Uri "$BaseUrl$Path" -Headers $headers -TimeoutSec 30
    } else {
        Invoke-RestMethod -Method Get -Uri "$BaseUrl$Path" -TimeoutSec 30
    }
}

function Invoke-PageGet {
    param([string]$Path)
    $headers = Get-AccessHeaders
    if ($headers.Count -gt 0) {
        Invoke-WebRequest -Method Get -Uri "$BaseUrl$Path" -Headers $headers -TimeoutSec 30
    } else {
        Invoke-WebRequest -Method Get -Uri "$BaseUrl$Path" -TimeoutSec 30
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

    throw "Server at $BaseUrl did not become ready within $TimeoutSec seconds. Start the app with .\scripts\dev.ps1 and try again."
}

Write-Host "Checking health endpoints..."
$health = Wait-ForServer -Path "/api/v1/healthz" -TimeoutSec $StartupTimeoutSec
Assert-Condition ($health.status -eq "ok") "healthz did not return ok"

Write-Host "Checking deployment readiness..."
$readiness = Wait-ForServer -Path "/api/v1/readinessz" -TimeoutSec $StartupTimeoutSec
Assert-Condition ($readiness.status -eq "ok") "readinessz did not return ok"
Assert-Condition ($readiness.checks.db.status -eq "ok") "readiness db check failed"
Assert-Condition ($readiness.checks.migrations.status -eq "ok") "readiness migration check failed"

$agentCard = Invoke-ApiGet "/.well-known/agent-card.json"
Assert-Condition ($agentCard.capabilities.streaming -eq $true) "agent-card streaming capability missing"
Assert-Condition ($agentCard.capabilities.push_notifications -eq $true) "agent-card push_notifications should be true"

Write-Host "Seeding demo data..."
& (Join-Path $PSScriptRoot "seed.ps1")

Write-Host "Checking seeded objects..."
$agents = Invoke-ApiGet "/api/v1/agents"
$sessions = Invoke-ApiGet "/api/v1/sessions"
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

$plannerAgentId = Get-AgentIdByDisplayName -Items $agents.agents -DisplayName "Planner"
$builderAgentId = Get-AgentIdByDisplayName -Items $agents.agents -DisplayName "Builder"
$reviewerAgentId = Get-AgentIdByDisplayName -Items $agents.agents -DisplayName "Reviewer"
Assert-Condition (-not [string]::IsNullOrWhiteSpace($plannerAgentId)) "planner demo agent missing"
Assert-Condition (-not [string]::IsNullOrWhiteSpace($builderAgentId)) "builder demo agent missing"
Assert-Condition (-not [string]::IsNullOrWhiteSpace($reviewerAgentId)) "reviewer demo agent missing"
Assert-Condition (@($sessions.sessions | Where-Object { $_.id -eq "ses_demo" }).Count -ge 1) "demo session missing"

Write-Host "Checking phase presets..."
$presets = Invoke-ApiGet "/api/v1/phases/presets"
$presetKeys = @($presets.presets | ForEach-Object { $_.phase_key })
Assert-Condition (($presetKeys -join ",") -eq "planning,implementation,review,revise,finalize") "phase presets are incomplete or out of order"

$sessionPhases = Invoke-ApiGet "/api/v1/sessions/ses_demo/phases"
$planningPhase = @($sessionPhases.phases | Where-Object { $_.phase_key -eq "planning" })[0]
Assert-Condition ($null -ne $planningPhase) "planning phase missing from session"
Assert-Condition ($planningPhase.is_active -eq $true) "planning phase should be active after seed"

Write-Host "Activating finalize phase..."
$finalizePhase = Invoke-ApiPost "/api/v1/sessions/ses_demo/phases/finalize/activate" @{}
Assert-Condition ($finalizePhase.phase.phase_key -eq "finalize") "finalize phase activation failed"

Write-Host "Posting a normal message..."
$messageResponse = Invoke-ApiPost "/api/v1/sessions/ses_demo/messages" @{
    sender_type       = "agent"
    sender_id         = $plannerAgentId
    content           = "hello from smoke"
    reply_to_message_id = $null
}
Assert-Condition (@($messageResponse.routing.created_jobs).Count -eq 0) "plain message should not create jobs"

$messages = Invoke-ApiGet "/api/v1/sessions/ses_demo/messages"
Assert-Condition (@($messages.messages).Count -ge 1) "expected at least one session message"

Write-Host "Creating a phase-aware command job..."
$jobCountBefore = @((Invoke-ApiGet "/api/v1/jobs?session_id=ses_demo").jobs).Count
$commandResponse = Invoke-ApiPost "/api/v1/sessions/ses_demo/messages" @{
    sender_type         = "agent"
    sender_id           = $plannerAgentId
    content             = "/new #builder smoke finalize handoff"
    reply_to_message_id = $null
    channel_key         = "general"
}
Assert-Condition ($commandResponse.message.message_type -eq "command") "command message was not recorded as a command"

$jobsAfter = @((Invoke-ApiGet "/api/v1/jobs?session_id=ses_demo").jobs)
Assert-Condition ($jobsAfter.Count -gt $jobCountBefore) "command did not create a new job"
$smokeJob = $jobsAfter | Sort-Object created_at, id | Select-Object -Last 1
Assert-Condition ($smokeJob.assigned_agent_id -eq $builderAgentId) "new job targeted the wrong agent"
Assert-Condition ($smokeJob.instructions -match "builder_to_reviewer") "finalize phase did not use the expected relay template"
Assert-Condition ($smokeJob.instructions -match "phase_key") "phase metadata missing from job instructions"
Assert-Condition ($smokeJob.instructions -match "finalize") "finalize phase metadata missing from job instructions"

Write-Host "Projecting the job into the experimental A2A adapter..."
$taskEnvelope = Invoke-ApiPost "/api/v1/a2a/jobs/$($smokeJob.id)/project" @{}
Assert-Condition ($taskEnvelope.task.job_id -eq $smokeJob.id) "A2A projection returned the wrong job id"
Assert-Condition ($taskEnvelope.task.phase_key -eq "finalize") "A2A projection did not carry the active phase"
Assert-Condition ($taskEnvelope.task.status -eq "queued") "A2A projection returned the wrong task status"

$taskList = Invoke-ApiGet "/api/v1/a2a/sessions/ses_demo/tasks"
Assert-Condition (@($taskList.tasks | Where-Object { $_.task_id -eq $taskEnvelope.task.task_id }).Count -ge 1) "projected A2A task missing from session task list"

Write-Host "Checking public A2A discovery and task flow..."
$publicAgentCard = Invoke-ApiGet "/.well-known/agent-card.json"
Assert-Condition ($publicAgentCard.api_version -eq "v1") "agent-card api_version missing"
Assert-Condition ($publicAgentCard.contract_version -eq "a2a.agent-card.v1") "agent-card contract_version missing"
Assert-Condition ($publicAgentCard.public_api_base_url -match "/api/v1/a2a$") "agent-card public API base URL missing"
Assert-Condition (@($publicAgentCard.endpoints | Where-Object { $_.name -eq "create_task" }).Count -ge 1) "agent-card public task endpoint missing"

$publicTaskEnvelope = Invoke-ApiPost "/api/v1/a2a/tasks" @{
    job_id = $smokeJob.id
}
Assert-Condition ($publicTaskEnvelope.task.job_id -eq $smokeJob.id) "public A2A task returned the wrong job id"
Assert-Condition ($publicTaskEnvelope.task.contract_version -eq "a2a.public.task.v1") "public A2A task contract missing"
Assert-Condition ($publicTaskEnvelope.task.status.state -eq "queued") "public A2A task status was wrong"

$publicTaskList = Invoke-ApiGet "/api/v1/a2a/tasks?session_id=ses_demo"
Assert-Condition (@($publicTaskList.tasks | Where-Object { $_.task_id -eq $publicTaskEnvelope.task.task_id }).Count -ge 1) "public A2A task missing from task list"

$publicSubscription = Invoke-ApiPost "/api/v1/a2a/tasks/$($publicTaskEnvelope.task.task_id)/subscriptions" @{
    since_sequence = 0
}
Assert-Condition ($publicSubscription.subscription.task_id -eq $publicTaskEnvelope.task.task_id) "public subscription returned the wrong task"
Assert-Condition ($publicSubscription.subscription.cursor_sequence -eq 0) "public subscription cursor should start at 0"

$publicTaskEvents = Invoke-ApiGet "/api/v1/a2a/tasks/$($publicTaskEnvelope.task.task_id)/events?since_sequence=0"
Assert-Condition (@($publicTaskEvents.events).Count -ge 1) "public A2A task events should include replayable data"
Assert-Condition ($publicTaskEvents.events[0].event_type -eq "created") "public A2A task events should start with created"

Write-Host "Checking operator shell..."
$shellPage = Invoke-PageGet "/operator"
Assert-Condition ($shellPage.Content -match "Operator Shell") "operator shell page did not render"
Assert-Condition ($shellPage.Content -match 'id="summary-cards"') "operator shell summary cards anchor missing"
Assert-Condition ($shellPage.Content -match 'id="session-list"') "operator shell session rail anchor missing"
Assert-Condition ($shellPage.Content -match 'id="operator-action-panel"') "operator shell action panel anchor missing"
Assert-Condition ($shellPage.Content -match 'id="operator-note"') "operator shell note anchor missing"
Assert-Condition ($shellPage.Content -match 'id="operator-action-buttons"') "operator shell action buttons anchor missing"
Assert-Condition ($shellPage.Content -match 'id="action-status-pill"') "operator shell action status anchor missing"
Assert-Condition ($shellPage.Content -match 'id="selected-session"') "operator shell selected session anchor missing"
Assert-Condition ($shellPage.Content -match 'id="dashboard-bottlenecks"') "operator shell dashboard anchor missing"
Assert-Condition ($shellPage.Content -match "/api/v1/operator/shell") "operator shell bootstrap path missing"

$shellBootstrap = Invoke-ApiGet "/api/v1/operator/shell?session_id=ses_demo"
Assert-Condition ($shellBootstrap.selected_session_id -eq "ses_demo") "operator shell bootstrap returned the wrong session"
Assert-Condition ($shellBootstrap.selected_session.session.id -eq "ses_demo") "operator shell selected session payload is wrong"
Assert-Condition ($shellBootstrap.sessions.Count -ge 1) "operator shell should include at least one session"
Assert-Condition ($shellBootstrap.dashboard.filters.session_id -eq "ses_demo") "operator shell dashboard filters lost the selected session id"
Assert-Condition ($shellBootstrap.selected_session.message_count -ge 2) "operator shell selected session should include transcript messages"
Assert-Condition ($shellBootstrap.selected_session.job_count -ge 1) "operator shell selected session should include jobs"
Assert-Condition ($shellBootstrap.selected_session.approval_count -ge 0) "operator shell selected session approval count missing"

Write-Host "Checking realtime operator activity..."
$activity = Invoke-ApiGet "/api/v1/operator/sessions/ses_demo/activity?since_sequence=0&limit=5"
Assert-Condition ($activity.session_id -eq "ses_demo") "operator activity returned the wrong session"
Assert-Condition (@($activity.events).Count -ge 1) "operator activity should include replayable events"
Assert-Condition (@($activity.signals.pending_approvals).Count -ge 0) "operator activity pending approvals missing"
Assert-Condition (@($activity.signals.stuck_jobs).Count -ge 0) "operator activity stuck jobs missing"

if ($IncludeRelay) {
    Write-Host "Posting a mention message to exercise relay..."
    $relayResponse = Invoke-ApiPost "/api/v1/sessions/ses_demo/messages" @{
        sender_type       = "agent"
        sender_id         = $builderAgentId
        content           = "#builder smoke relay"
        reply_to_message_id = $null
    }
    Assert-Condition (@($relayResponse.routing.created_jobs).Count -ge 1) "mention message should create at least one job"
    $jobId = @($relayResponse.routing.created_jobs)[0]
    $job = Invoke-ApiGet "/api/v1/jobs/$jobId"
    Assert-Condition ($job.job.job.id -eq $jobId) "job detail endpoint returned the wrong job"
}

Write-Host "Smoke checks passed."
