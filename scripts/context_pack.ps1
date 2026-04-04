[CmdletBinding()]
param(
    [ValidateSet("minimal", "implementation", "full")]
    [string]$Mode = "minimal",
    [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

function Get-DocText {
    param(
        [Parameter(Mandatory)]
        [string]$Path,
        [int]$MaxLines = 0
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Missing doc path: $Path"
    }

    if ($MaxLines -gt 0) {
        return (Get-Content -LiteralPath $Path -Encoding UTF8 -TotalCount $MaxLines) -join "`n"
    }

    return (Get-Content -LiteralPath $Path -Encoding UTF8) -join "`n"
}

function Append-Section {
    param(
        [Parameter(Mandatory)]
        [System.Text.StringBuilder]$Builder,
        [Parameter(Mandatory)]
        [string]$Path,
        [int]$MaxLines = 0
    )

    [void]$Builder.AppendLine("===== FILE: $Path =====")
    [void]$Builder.AppendLine("")
    [void]$Builder.AppendLine((Get-DocText -Path $Path -MaxLines $MaxLines))
    [void]$Builder.AppendLine("")
}

$sections = [System.Collections.Generic.List[object]]::new()

switch ($Mode) {
    "minimal" {
        $sections.Add(@{ path = "docs/_meta/CONTEXT_PACK_256K.md"; max_lines = 0 })
        $sections.Add(@{ path = "README.md"; max_lines = 0 })
        $sections.Add(@{ path = "AGENTS.md"; max_lines = 0 })
        $sections.Add(@{ path = "docs/planning/STATUS.md"; max_lines = 0 })
    }
    "implementation" {
        $sections.Add(@{ path = "docs/_meta/CONTEXT_PACK_256K.md"; max_lines = 0 })
        $sections.Add(@{ path = "README.md"; max_lines = 0 })
        $sections.Add(@{ path = "AGENTS.md"; max_lines = 0 })
        $sections.Add(@{ path = "docs/planning/STATUS.md"; max_lines = 0 })
        $sections.Add(@{ path = "docs/planning/IMPLEMENTATION_V8.md"; max_lines = 0 })
        $sections.Add(@{ path = "docs/reference/ARCHITECTURE.md"; max_lines = 240 })
        $sections.Add(@{ path = "docs/reference/API.md"; max_lines = 260 })
        $sections.Add(@{ path = "docs/reference/DB_SCHEMA.md"; max_lines = 260 })
        $sections.Add(@{ path = "docs/operations/LOCAL_SETUP.md"; max_lines = 0 })
        $sections.Add(@{ path = "docs/operator/OPERATOR_UI.md"; max_lines = 0 })
        $sections.Add(@{ path = "scripts/README.md"; max_lines = 0 })
    }
    "full" {
        $sections.Add(@{ path = "docs/_meta/CONTEXT_PACK_256K.md"; max_lines = 0 })
        $sections.Add(@{ path = "README.md"; max_lines = 0 })
        $sections.Add(@{ path = "AGENTS.md"; max_lines = 0 })
        $sections.Add(@{ path = "docs/planning/INDEX.md"; max_lines = 0 })
        $sections.Add(@{ path = "docs/planning/STATUS.md"; max_lines = 0 })
        $sections.Add(@{ path = "docs/planning/PLAN_V8.md"; max_lines = 0 })
        $sections.Add(@{ path = "docs/planning/IMPLEMENTATION_V8.md"; max_lines = 0 })
        $sections.Add(@{ path = "docs/reference/INDEX.md"; max_lines = 0 })
        $sections.Add(@{ path = "docs/reference/ARCHITECTURE.md"; max_lines = 0 })
        $sections.Add(@{ path = "docs/reference/API.md"; max_lines = 0 })
        $sections.Add(@{ path = "docs/reference/DB_SCHEMA.md"; max_lines = 0 })
        $sections.Add(@{ path = "docs/operations/LOCAL_SETUP.md"; max_lines = 0 })
        $sections.Add(@{ path = "docs/operator/OPERATOR_UI.md"; max_lines = 0 })
        $sections.Add(@{ path = "scripts/README.md"; max_lines = 0 })
    }
}

$builder = [System.Text.StringBuilder]::new()
[void]$builder.AppendLine("# Context Pack Output")
[void]$builder.AppendLine("")
[void]$builder.AppendLine("mode: $Mode")
[void]$builder.AppendLine("generated_at_utc: $([DateTime]::UtcNow.ToString('o'))")
[void]$builder.AppendLine("")

foreach ($section in $sections) {
    Append-Section -Builder $builder -Path $section.path -MaxLines $section.max_lines
}

$output = $builder.ToString().TrimEnd()
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $output
    exit 0
}

$parent = Split-Path -Parent $OutputPath
if ([string]::IsNullOrWhiteSpace($parent)) {
    $parent = "."
}
if (-not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}
Set-Content -LiteralPath $OutputPath -Encoding UTF8 -Value $output
Write-Host "Wrote context pack to $OutputPath"
