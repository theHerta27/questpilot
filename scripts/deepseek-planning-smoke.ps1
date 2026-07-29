param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$taskPath = Join-Path $projectRoot "backend\tests\fixtures\deepseek_planning_tasks.json"
$parsedTasks = Get-Content -Raw -Encoding UTF8 $taskPath | ConvertFrom-Json
$tasks = @()
foreach ($item in $parsedTasks) {
    $tasks += $item
}
if ($tasks.Count -lt 8 -or $tasks.Count -gt 12) {
    throw "Planning smoke manifest must contain 8 to 12 tasks; found $($tasks.Count)."
}
$results = @()

function Invoke-Json {
    param([string]$Method, [string]$Url, [object]$Body)
    $arguments = @{
        UseBasicParsing = $true
        Method = $Method
        Uri = $Url
        TimeoutSec = 90
    }
    if ($null -ne $Body) {
        $arguments.ContentType = "application/json; charset=utf-8"
        $arguments.Body = [Text.Encoding]::UTF8.GetBytes(
            ($Body | ConvertTo-Json -Depth 14)
        )
    }
    $response = Invoke-WebRequest @arguments
    $text = [Text.Encoding]::UTF8.GetString($response.RawContentStream.ToArray())
    return $text | ConvertFrom-Json
}

foreach ($task in $tasks) {
    Write-Host "Running $($task.id)..." -NoNewline
    $started = Get-Date
    try {
        $userId = "planning-$($task.id)"
        $parsed = Invoke-Json "POST" "$BaseUrl/api/v1/agent/parse-goals" @{
            query = $task.query
            user_id = $userId
            locale = "zh-CN"
        }
        $resolved = @($parsed.resolved_goals)
        $groups = @($parsed.candidate_groups)
        $collectionNos = @(
            $resolved |
                ForEach-Object { [int]$_.character.collection_no } |
                Sort-Object -Unique
        )
        $expectedNos = @($task.expected_collection_nos | ForEach-Object { [int]$_ })
        $checks = @(
            $resolved.Count -eq [int]$task.expected_goal_count
            (($groups.Count -gt 0) -eq [bool]$task.requires_selection)
            (@($parsed.tool_steps | Where-Object name -eq "propose_training_goals").Count -eq 1)
            (@($parsed.tool_steps | Where-Object name -eq "search_character").Count -ge 1)
            (($collectionNos -join ",") -eq ($expectedNos -join ","))
        )
        $plan = $null
        $planTrace = $null
        if (-not [bool]$task.requires_selection) {
            $goals = @(
                $resolved | ForEach-Object {
                    @{
                        character_id = [int]$_.character_id
                        skill_number = [int]$_.skill_number
                        current_level = [int]$_.current_level
                        target_level = [int]$_.target_level
                    }
                }
            )
            Invoke-Json "PUT" "$BaseUrl/api/v1/account/inventory" @{
                user_id = $userId
                mode = "replace"
                items = @()
            } | Out-Null
            $plan = Invoke-Json "POST" "$BaseUrl/api/v1/plans" @{
                user_id = $userId
                goals = $goals
                current_ap = 50000
                golden_apples = 0
                daily_minutes = 1440
                minutes_per_run = 3
                planner_node_limit = 50000
                planner_timeout_ms = 750
            }
            $planTrace = Invoke-Json "GET" "$BaseUrl/api/v1/traces/$($plan.run_id)" $null
            $checks += [bool]$plan.verified
            $checks += $plan.dataset_version -eq "1779642278"
            $checks += $plan.candidate_scope -like "13 *"
            $checks += $plan.solver -in @("bounded-branch-and-bound", "greedy-baseline")
            $checks += @(
                $planTrace.events |
                    Where-Object {
                        $_.component -eq "DeterministicPlanValidator" -and
                        $_.event_type -eq "verification.completed"
                    }
            ).Count -eq 1
            $checks += @($planTrace.events | Where-Object { $_.event_type -like "model.*" }).Count -eq 0
        }
        else {
            $checks += $groups.Count -ge 1
        }
        $passed = $checks -notcontains $false
        $results += [PSCustomObject]@{
            id = $task.id
            passed = $passed
            parse_run_id = $parsed.run_id
            plan_run_id = if ($plan) { $plan.run_id } else { $null }
            resolved_count = $resolved.Count
            candidate_group_count = $groups.Count
            collection_nos = $collectionNos
            plan_status = if ($plan) { $plan.status } else { "requires_selection" }
            solver = if ($plan) { $plan.solver } else { $null }
            optimality = if ($plan) { $plan.optimality } else { $null }
            duration_ms = [int](((Get-Date) - $started).TotalMilliseconds)
            error = $null
        }
        Write-Host $(if ($passed) { " PASS" } else { " FAIL" })
    }
    catch {
        $results += [PSCustomObject]@{
            id = $task.id
            passed = $false
            duration_ms = [int](((Get-Date) - $started).TotalMilliseconds)
            error = $_.Exception.Message
        }
        Write-Host " ERROR"
    }
}

$passedCount = @($results | Where-Object passed).Count
$report = [PSCustomObject]@{
    suite_name = "DeepSeek natural-language constrained planning smoke"
    model = "deepseek-v4-flash"
    thinking = "disabled"
    dataset_version = "1779642278"
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    task_count = $results.Count
    passed = $passedCount
    failed = $results.Count - $passedCount
    results = $results
}
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $projectRoot "reports\generated\deepseek-planning-smoke.json"
}
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutputPath) | Out-Null
$report | ConvertTo-Json -Depth 12 | Set-Content -Encoding UTF8 -LiteralPath $OutputPath
Write-Host ""
Write-Host "DeepSeek planning smoke: $passedCount/$($results.Count) passed"
Write-Host "Report: $OutputPath"
if ($passedCount -ne $results.Count) {
    exit 1
}
