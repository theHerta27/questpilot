param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$OutputPath = "",
    [string[]]$TaskId = @()
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$taskPath = Join-Path $projectRoot "backend\tests\fixtures\deepseek_smoke_tasks.json"
$parsedTasks = Get-Content -Raw -Encoding UTF8 $taskPath | ConvertFrom-Json
$tasks = @()
foreach ($item in $parsedTasks) {
    $tasks += $item
}
if ($tasks.Count -lt 10 -or $tasks.Count -gt 20) {
    throw "Smoke task manifest must contain 10 to 20 tasks; found $($tasks.Count)."
}
if ($TaskId.Count) {
    $tasks = @($tasks | Where-Object { $TaskId -contains $_.id })
    if ($tasks.Count -ne $TaskId.Count) {
        throw "One or more requested smoke task IDs were not found."
    }
}
$results = @()

function Invoke-Json {
    param(
        [string]$Method,
        [string]$Url,
        [object]$Body
    )
    if ($null -eq $Body) {
        $response = Invoke-WebRequest -UseBasicParsing -Method $Method -Uri $Url
    }
    else {
        $json = $Body | ConvertTo-Json -Depth 10
        $bytes = [Text.Encoding]::UTF8.GetBytes($json)
        $response = Invoke-WebRequest `
            -UseBasicParsing `
            -Method $Method `
            -Uri $Url `
            -ContentType "application/json; charset=utf-8" `
            -Body $bytes `
            -TimeoutSec 90
    }
    $text = [Text.Encoding]::UTF8.GetString($response.RawContentStream.ToArray())
    return $text | ConvertFrom-Json
}

foreach ($task in $tasks) {
    Write-Host "Running $($task.id)..." -NoNewline
    $started = Get-Date
    try {
        $response = Invoke-Json `
            -Method "POST" `
            -Url "$BaseUrl/api/v1/agent/query" `
            -Body @{query=$task.query; user_id="deepseek-smoke"; locale="zh-CN"}
        $trace = Invoke-Json `
            -Method "GET" `
            -Url "$BaseUrl/api/v1/traces/$($response.run_id)" `
            -Body $null
        $toolStarts = @($trace.events | Where-Object { $_.event_type -eq "tool.started" })
        $toolNames = @($toolStarts | ForEach-Object { $_.component })
        $searchResults = @(
            $trace.events |
                Where-Object {
                    $_.event_type -eq "tool.completed" -and
                    $_.component -eq "search_character"
                } |
                ForEach-Object { @($_.payload_summary.result.characters) }
        )
        $collectionNumbers = @(
            $searchResults |
                ForEach-Object { [int]$_.collection_no } |
                Sort-Object -Unique
        )
        $gapStarts = @(
            $toolStarts |
                Where-Object { $_.component -eq "calculate_material_gap" }
        )
        $goalCount = if ($gapStarts.Count) {
            @($gapStarts[-1].payload_summary.arguments.goals).Count
        }
        else {
            0
        }

        $checks = @()
        foreach ($required in @($task.required_tools)) {
            $checks += $toolNames -contains $required
        }
        foreach ($forbidden in @($task.forbidden_tools)) {
            $checks += $toolNames -notcontains $forbidden
        }
        foreach ($expectedNo in @($task.expected_collection_nos)) {
            $checks += $collectionNumbers -contains [int]$expectedNo
        }
        if ($null -ne $task.minimum_goal_count) {
            $checks += $goalCount -ge [int]$task.minimum_goal_count
        }
        $answerTerms = @($task.answer_terms_any)
        if ($answerTerms.Count) {
            $checks += @(
                $answerTerms |
                    Where-Object { $response.answer -like "*$_*" }
            ).Count -gt 0
        }
        $checks += -not [string]::IsNullOrWhiteSpace($response.answer)
        $passed = $checks -notcontains $false
        $results += [PSCustomObject]@{
            id = $task.id
            passed = $passed
            run_id = $response.run_id
            tools = $toolNames
            collection_nos = $collectionNumbers
            goal_count = $goalCount
            event_count = $response.event_count
            duration_ms = [int](((Get-Date) - $started).TotalMilliseconds)
            answer = $response.answer
            error = $null
        }
        Write-Host $(if ($passed) { " PASS" } else { " FAIL" })
    }
    catch {
        $results += [PSCustomObject]@{
            id = $task.id
            passed = $false
            run_id = $null
            tools = @()
            collection_nos = @()
            goal_count = 0
            event_count = 0
            duration_ms = [int](((Get-Date) - $started).TotalMilliseconds)
            answer = ""
            error = $_.Exception.Message
        }
        Write-Host " ERROR"
    }
}

$passedCount = @($results | Where-Object passed).Count
$report = [PSCustomObject]@{
    suite_name = "DeepSeek V4 Flash natural-language smoke"
    model = "deepseek-v4-flash"
    thinking = "disabled"
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    task_count = $results.Count
    passed = $passedCount
    failed = $results.Count - $passedCount
    results = $results
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputPath = Join-Path $projectRoot "reports\generated\deepseek-smoke-$stamp.json"
}
$outputDir = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
$report | ConvertTo-Json -Depth 12 | Set-Content -Encoding UTF8 -LiteralPath $OutputPath

Write-Host ""
Write-Host "DeepSeek smoke: $passedCount/$($results.Count) passed"
Write-Host "Report: $OutputPath"
if ($passedCount -ne $results.Count) {
    exit 1
}
