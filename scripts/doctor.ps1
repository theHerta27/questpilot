$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$checks = @()

function Add-Check {
    param(
        [string]$Name,
        [bool]$Passed,
        [string]$Detail
    )
    $script:checks += [PSCustomObject]@{
        Check = $Name
        Status = if ($Passed) { "OK" } else { "FAIL" }
        Detail = $Detail
    }
}

function Test-TcpPort {
    param([string]$HostName, [int]$Port)
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect($HostName, $Port, $null, $null)
        return $async.AsyncWaitHandle.WaitOne(500) -and $client.Connected
    }
    finally {
        $client.Dispose()
    }
}

$uv = Get-Command uv -ErrorAction SilentlyContinue
$node = Get-Command node -ErrorAction SilentlyContinue
$npm = Get-Command npm -ErrorAction SilentlyContinue
$envPath = Join-Path $projectRoot ".env"
$backendPython = Join-Path $projectRoot "backend\.venv\Scripts\python.exe"
$frontendModules = Join-Path $projectRoot "frontend\node_modules"

Add-Check "uv" ($null -ne $uv) $(if ($uv) { $uv.Source } else { "Run uv sync --extra dev" })
Add-Check "Node.js" ($null -ne $node) $(if ($node) { $node.Source } else { "Install Node.js 22+" })
Add-Check "npm" ($null -ne $npm) $(if ($npm) { $npm.Source } else { "Install npm" })
Add-Check ".env" (Test-Path $envPath) "Project root .env"
Add-Check "Backend deps" (Test-Path $backendPython) "backend\.venv"
Add-Check "Frontend deps" (Test-Path $frontendModules) "frontend\node_modules"
Add-Check "PostgreSQL" (Test-TcpPort "127.0.0.1" 5432) "127.0.0.1:5432"

$apiRunning = Test-TcpPort "127.0.0.1" 8000
$webRunning = Test-TcpPort "127.0.0.1" 5173
Add-Check "API port" $true $(if ($apiRunning) { "127.0.0.1:8000 is listening" } else { "Available" })
Add-Check "Web port" $true $(if ($webRunning) { "127.0.0.1:5173 is listening" } else { "Available" })

$checks | Format-Table -AutoSize

$failed = @($checks | Where-Object { $_.Status -eq "FAIL" })
if ($failed.Count -gt 0) {
    throw "Environment checks failed: $($failed.Check -join ', ')"
}

Write-Host "QuestPilot environment checks passed." -ForegroundColor Green
