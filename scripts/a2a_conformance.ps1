[CmdletBinding()]
param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$DatabaseUrl = $(if ([string]::IsNullOrWhiteSpace($env:DATABASE_URL)) {
            "sqlite:///./codex_coordinator.db"
        } else {
            $env:DATABASE_URL
        }),
    [int]$StartupTimeoutSec = 60,
    [int]$WebhookTimeoutSec = 20
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

$env:DATABASE_URL = $DatabaseUrl
$BaseUrl = $BaseUrl.TrimEnd("/")

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
    $headers[$headerName] = $env:ACCESS_TOKEN
    return $headers
}

function Get-BootstrapOperatorHeaders {
    $headers = Get-AccessHeaders
    $actorIdHeader = $(if ([string]::IsNullOrWhiteSpace($env:ACTOR_ID_HEADER)) { "X-Actor-Id" } else { $env:ACTOR_ID_HEADER })
    $actorRoleHeader = $(if ([string]::IsNullOrWhiteSpace($env:ACTOR_ROLE_HEADER)) { "X-Actor-Role" } else { $env:ACTOR_ROLE_HEADER })
    $actorTypeHeader = $(if ([string]::IsNullOrWhiteSpace($env:ACTOR_TYPE_HEADER)) { "X-Actor-Type" } else { $env:ACTOR_TYPE_HEADER })
    $actorLabelHeader = $(if ([string]::IsNullOrWhiteSpace($env:ACTOR_LABEL_HEADER)) { "X-Actor-Label" } else { $env:ACTOR_LABEL_HEADER })
    $headers[$actorIdHeader] = $(if ([string]::IsNullOrWhiteSpace($env:ACTOR_ID)) { "ops_conformance" } else { $env:ACTOR_ID })
    $headers[$actorRoleHeader] = $(if ([string]::IsNullOrWhiteSpace($env:ACTOR_ROLE)) { "operator" } else { $env:ACTOR_ROLE })
    $headers[$actorTypeHeader] = $(if ([string]::IsNullOrWhiteSpace($env:ACTOR_TYPE)) { "human" } else { $env:ACTOR_TYPE })
    $headers[$actorLabelHeader] = $(if ([string]::IsNullOrWhiteSpace($env:ACTOR_LABEL)) { "A2A conformance operator" } else { $env:ACTOR_LABEL })
    return $headers
}

function Get-BearerHeaders {
    param(
        [string]$Secret
    )

    return @{
        "Authorization" = "Bearer $Secret"
    }
}

function Merge-Headers {
    param(
        [hashtable]$Base,
        [hashtable]$Extra
    )

    $merged = @{}
    foreach ($key in $Base.Keys) {
        $merged[$key] = $Base[$key]
    }
    foreach ($key in $Extra.Keys) {
        $merged[$key] = $Extra[$key]
    }
    return $merged
}

function Invoke-ApiGet {
    param(
        [string]$Path,
        [hashtable]$Headers = @{}
    )

    if ($Headers.Count -gt 0) {
        return Invoke-RestMethod -Method Get -Uri "$BaseUrl$Path" -Headers $Headers -TimeoutSec 30
    }

    return Invoke-RestMethod -Method Get -Uri "$BaseUrl$Path" -TimeoutSec 30
}

function Invoke-ApiPost {
    param(
        [string]$Path,
        [object]$Body,
        [hashtable]$Headers = @{}
    )

    $payload = if ($Body -is [string]) {
        $Body
    } else {
        $Body | ConvertTo-Json -Depth 12
    }
    if ($Headers.Count -gt 0) {
        return Invoke-RestMethod -Method Post -Uri "$BaseUrl$Path" -Headers $Headers -ContentType "application/json" -Body $payload -TimeoutSec 30
    }

    return Invoke-RestMethod -Method Post -Uri "$BaseUrl$Path" -ContentType "application/json" -Body $payload -TimeoutSec 30
}

function Invoke-StreamGet {
    param(
        [string]$Path,
        [hashtable]$Headers = @{}
    )

    if ($Headers.Count -gt 0) {
        return Invoke-WebRequest -Method Get -Uri "$BaseUrl$Path" -Headers $Headers -TimeoutSec 30
    }

    return Invoke-WebRequest -Method Get -Uri "$BaseUrl$Path" -TimeoutSec 30
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

function Write-Check {
    param(
        [string]$Name
    )

    Write-Host ("[pass] " + $Name)
}

function Wait-ForServer {
    param(
        [string]$Path,
        [int]$TimeoutSec
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            return Invoke-ApiGet -Path $Path
        } catch {
            Start-Sleep -Seconds 1
        }
    }

    throw "Server at $BaseUrl did not become ready within $TimeoutSec seconds."
}

function Wait-ForFileContent {
    param(
        [string]$Path,
        [int]$TimeoutSec
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if ((Test-Path -LiteralPath $Path) -and ((Get-Item -LiteralPath $Path).Length -gt 0)) {
            return Get-Content -LiteralPath $Path -Raw
        }
        Start-Sleep -Milliseconds 200
    }

    throw "Timed out waiting for webhook receiver capture at $Path."
}

function Get-FreeTcpPort {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    try {
        return ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
    } finally {
        $listener.Stop()
    }
}

function Start-WebhookReceiver {
    param(
        [int]$Port,
        [string]$CapturePath
    )

    $prefix = "http://127.0.0.1:$Port/"
    $job = Start-Job -ArgumentList $prefix, $CapturePath -ScriptBlock {
        param($ReceiverPrefix, $ReceiverCapturePath)
        $listener = [System.Net.HttpListener]::new()
        $listener.Prefixes.Add($ReceiverPrefix)
        $listener.Start()
        try {
            $context = $listener.GetContext()
            $request = $context.Request
            $reader = [System.IO.StreamReader]::new($request.InputStream, $request.ContentEncoding)
            try {
                $body = $reader.ReadToEnd()
            } finally {
                $reader.Dispose()
            }
            $headers = @{}
            foreach ($key in $request.Headers.AllKeys) {
                $headers[$key] = $request.Headers[$key]
            }
            [pscustomobject]@{
                path = $request.Url.AbsolutePath
                headers = $headers
                body = $body
            } | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $ReceiverCapturePath -Encoding UTF8

            $response = $context.Response
            $response.StatusCode = 200
            $payload = [System.Text.Encoding]::UTF8.GetBytes("ok")
            $response.OutputStream.Write($payload, 0, $payload.Length)
            $response.OutputStream.Close()
        } finally {
            $listener.Stop()
            $listener.Close()
        }
    }

    return @{
        Prefix = $prefix
        Job = $job
    }
}

function Stop-WebhookReceiver {
    param(
        [hashtable]$Receiver
    )

    if ($null -eq $Receiver -or $null -eq $Receiver.Job) {
        return
    }

    try {
        Stop-Job -Job $Receiver.Job -ErrorAction SilentlyContinue | Out-Null
    } finally {
        Remove-Job -Job $Receiver.Job -Force -ErrorAction SilentlyContinue | Out-Null
    }
}

function Wait-WebhookReceiver {
    param(
        [int]$Port,
        [int]$TimeoutSec = 5
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $client = [System.Net.Sockets.TcpClient]::new()
        try {
            $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
            if ($async.AsyncWaitHandle.WaitOne(200) -and $client.Connected) {
                $client.EndConnect($async)
                return
            }
        } catch {
        } finally {
            $client.Dispose()
        }
        Start-Sleep -Milliseconds 100
    }

    throw "Timed out waiting for webhook receiver on port $Port."
}

function Convert-BytesToHex {
    param(
        [byte[]]$Bytes
    )

    return ([System.BitConverter]::ToString($Bytes)).Replace("-", "").ToLowerInvariant()
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

$receiver = $null
$captureFile = Join-Path ([System.IO.Path]::GetTempPath()) ("ccc-a2a-conformance-{0}.json" -f ([guid]::NewGuid().ToString("N")))

try {
    Write-Host "Waiting for the app to become ready..."
    Wait-ForServer -Path "/api/v1/healthz" -TimeoutSec $StartupTimeoutSec | Out-Null
    Wait-ForServer -Path "/api/v1/readinessz" -TimeoutSec $StartupTimeoutSec | Out-Null

    Write-Host "Seeding demo data..."
    & (Join-Path $PSScriptRoot "seed.ps1")

    $bootstrapHeaders = Get-BootstrapOperatorHeaders

    Write-Host "Creating demo job for projection..."
    $agents = Invoke-ApiGet -Path "/api/v1/agents" -Headers $bootstrapHeaders
    $plannerAgentId = Get-AgentIdByDisplayName -Items $agents.agents -DisplayName "Planner"
    $builderAgentId = Get-AgentIdByDisplayName -Items $agents.agents -DisplayName "Builder"
    Assert-Condition (-not [string]::IsNullOrWhiteSpace($plannerAgentId)) "Planner demo agent missing"
    Assert-Condition (-not [string]::IsNullOrWhiteSpace($builderAgentId)) "Builder demo agent missing"
    $jobsBefore = @((Invoke-ApiGet -Path "/api/v1/jobs?session_id=ses_demo" -Headers $bootstrapHeaders).jobs)
    $commandResponse = Invoke-ApiPost -Path "/api/v1/sessions/ses_demo/messages" -Headers $bootstrapHeaders -Body @{
        sender_type = "agent"
        sender_id = $plannerAgentId
        content = "/new #builder a2a conformance"
        reply_to_message_id = $null
        channel_key = "general"
    }
    Assert-Condition ($commandResponse.message.message_type -eq "command") "Conformance seed command was not recorded as a command"
    $jobsAfter = @((Invoke-ApiGet -Path "/api/v1/jobs?session_id=ses_demo" -Headers $bootstrapHeaders).jobs)
    Assert-Condition ($jobsAfter.Count -gt $jobsBefore.Count) "Conformance seed command did not create a job"
    $job = $jobsAfter | Sort-Object created_at, id | Select-Object -Last 1
    $jobId = $job.id

    Write-Host "Issuing managed integration credential..."
    $principalEnvelope = Invoke-ApiPost -Path "/api/v1/operator/integration-principals" -Headers $bootstrapHeaders -Body @{
        display_label = "A2A Conformance"
        principal_type = "service_account"
        actor_role = "operator"
        actor_type = "service"
        default_scopes = @("operator_write")
        notes = "Early-adopter conformance verification"
    }
    $credentialEnvelope = Invoke-ApiPost -Path "/api/v1/operator/integration-principals/$($principalEnvelope.principal.id)/credentials" -Headers $bootstrapHeaders -Body @{
        label = "a2a-conformance"
        scopes = @("operator_write")
        note = "Managed credential for supported A2A conformance flow"
    }
    $credentialSecret = $credentialEnvelope.secret_value
    Assert-Condition (-not [string]::IsNullOrWhiteSpace($credentialSecret)) "Managed credential did not return a secret"
    $credentialHeaders = Get-BearerHeaders -Secret $credentialSecret

    Write-Host "Verifying discovery contract..."
    $agentCard = Invoke-ApiGet -Path "/.well-known/agent-card.json" -Headers $credentialHeaders
    $endpointPaths = @($agentCard.endpoints | ForEach-Object { $_.path })
    Assert-Condition ($agentCard.contract_version -eq "a2a.agent-card.v1") "Unexpected agent-card contract version"
    Assert-Condition ($endpointPaths -contains "/api/v1/a2a/tasks") "agent-card missing task route"
    Assert-Condition ($endpointPaths -contains "/api/v1/a2a/tasks/{task_id}/events") "agent-card missing replay route"
    Assert-Condition ($endpointPaths -contains "/api/v1/a2a/subscriptions/{subscription_id}/events") "agent-card missing SSE route"
    Assert-Condition (-not ($endpointPaths -contains "/api/v1/a2a/jobs/{job_id}/project")) "Legacy bridge route must not be advertised"
    $compatibilityNotes = @($agentCard.compatibility_notes)
    Assert-Condition (@($compatibilityNotes | Where-Object { $_ -match "Managed integration credentials" }).Count -ge 1) "agent-card must mention managed credentials"
    Assert-Condition (@($compatibilityNotes | Where-Object { $_ -match "outbound webhooks" }).Count -ge 1) "agent-card must mention managed outbound webhooks"
    Write-Check "discovery"

    Write-Host "Projecting public task with managed credential..."
    $taskEnvelope = Invoke-ApiPost -Path "/api/v1/a2a/tasks" -Headers $credentialHeaders -Body @{
        job_id = $jobId
    }
    $taskId = $taskEnvelope.task.task_id
    Assert-Condition ($taskEnvelope.task.contract_version -eq "a2a.public.task.v1") "Unexpected task contract version"
    $taskList = Invoke-ApiGet -Path "/api/v1/a2a/tasks?session_id=ses_demo" -Headers $credentialHeaders
    Assert-Condition ((@($taskList.tasks | Where-Object { $_.task_id -eq $taskId }).Count) -eq 1) "Projected task missing from list"
    $taskById = Invoke-ApiGet -Path "/api/v1/a2a/tasks/$taskId" -Headers $credentialHeaders
    Assert-Condition ($taskById.task.task_id -eq $taskId) "Task lookup returned wrong task id"
    Write-Check "task projection"

    Write-Host "Verifying replay and SSE..."
    $subscriptionEnvelope = Invoke-ApiPost -Path "/api/v1/a2a/tasks/$taskId/subscriptions" -Headers $credentialHeaders -Body @{
        since_sequence = 0
    }
    Assert-Condition ($subscriptionEnvelope.subscription.contract_version -eq "a2a.public.task.subscription.v1") "Unexpected subscription contract version"
    $subscriptionLookup = Invoke-ApiGet -Path "/api/v1/a2a/subscriptions/$($subscriptionEnvelope.subscription.subscription_id)" -Headers $credentialHeaders
    Assert-Condition ($subscriptionLookup.subscription.subscription_id -eq $subscriptionEnvelope.subscription.subscription_id) "Subscription lookup returned wrong id"
    $eventsEnvelope = Invoke-ApiGet -Path "/api/v1/a2a/tasks/$taskId/events?since_sequence=0" -Headers $credentialHeaders
    Assert-Condition (@($eventsEnvelope.events).Count -ge 1) "Replay must return at least one event"
    Assert-Condition ($eventsEnvelope.events[0].contract_version -eq "a2a.public.task.event.v1") "Unexpected event contract version"
    $streamResponse = Invoke-StreamGet -Path "/api/v1/a2a/subscriptions/$($subscriptionEnvelope.subscription.subscription_id)/events" -Headers $credentialHeaders
    Assert-Condition ($streamResponse.Content -match '"contract_version": "a2a.public.task.event.stream.v1"') "SSE stream missing contract version marker"
    Assert-Condition ($streamResponse.Content -match '"delivery_mode": "sse"') "SSE stream missing delivery mode"
    Write-Check "replay and sse"

    Write-Host "Registering webhook and verifying delivery..."
    $port = Get-FreeTcpPort
    $receiver = Start-WebhookReceiver -Port $port -CapturePath $captureFile
    Wait-WebhookReceiver -Port $port
    $webhookSecret = "conformance-secret"
    $webhookEnvelope = Invoke-ApiPost -Path "/api/v1/operator/a2a/tasks/$taskId/webhooks" -Headers $credentialHeaders -Body @{
        target_url = "http://127.0.0.1:$port/hook"
        signing_secret = $webhookSecret
        description = "A2A conformance receiver"
    }
    Assert-Condition ($webhookEnvelope.webhook.status -eq "active") "Webhook registration did not become active"

    $cancelResponse = Invoke-ApiPost -Path "/api/v1/operator/jobs/$jobId/cancel" -Headers $credentialHeaders -Body @{
        reason = "a2a conformance"
        note = "Generate a supported public task status transition"
    }
    Assert-Condition ($cancelResponse.action.outcome -eq "applied") "Operator cancel action did not apply"
    Invoke-ApiPost -Path "/api/v1/a2a/tasks" -Headers $credentialHeaders -Body @{
        job_id = $jobId
    } | Out-Null

    $captureJson = Wait-ForFileContent -Path $captureFile -TimeoutSec $WebhookTimeoutSec
    $capture = $captureJson | ConvertFrom-Json
    $signatureHeader = $capture.headers.'X-CCC-Signature'
    Assert-Condition (-not [string]::IsNullOrWhiteSpace($signatureHeader)) "Webhook receiver did not capture signature header"
    $hmac = [System.Security.Cryptography.HMACSHA256]::new([System.Text.Encoding]::UTF8.GetBytes($webhookSecret))
    try {
        $hash = $hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes([string]$capture.body))
    } finally {
        $hmac.Dispose()
    }
    $expectedSignature = "sha256=" + (Convert-BytesToHex -Bytes $hash)
    Assert-Condition ($signatureHeader -eq $expectedSignature) "Webhook signature mismatch"
    Assert-Condition ($capture.headers.'X-CCC-Task-Id' -eq $taskId) "Webhook task id header mismatch"
    Assert-Condition ([int]$capture.headers.'X-CCC-Event-Sequence' -ge 1) "Webhook event sequence missing"

    $deliveryList = Invoke-ApiGet -Path "/api/v1/operator/a2a/tasks/$taskId/webhook-deliveries" -Headers $credentialHeaders
    Assert-Condition ((@($deliveryList.deliveries | Where-Object { $_.status -eq "delivered" }).Count) -ge 1) "Webhook delivery list missing delivered row"
    Write-Check "managed outbound webhook"

    Write-Host "A2A conformance summary"
    Write-Host ("  Job id: " + $jobId)
    Write-Host ("  Task id: " + $taskId)
    Write-Host ("  Subscription id: " + $subscriptionEnvelope.subscription.subscription_id)
    Write-Host ("  Credential id: " + $credentialEnvelope.credential.id)
    Write-Host ("  Webhook id: " + $webhookEnvelope.webhook.id)
    Write-Host "Conformance checks passed."
} finally {
    Stop-WebhookReceiver -Receiver $receiver
    Remove-Item -LiteralPath $captureFile -Force -ErrorAction SilentlyContinue
}
