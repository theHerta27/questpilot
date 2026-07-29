$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runtimeDir = Join-Path $projectRoot ".runtime"
$backendDir = Join-Path $projectRoot "backend"
$frontendDir = Join-Path $projectRoot "frontend"

New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null

function Test-Http {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 400
    }
    catch {
        return $false
    }
}

function Wait-Http {
    param(
        [string]$Name,
        [string]$Url,
        [System.Diagnostics.Process]$Process,
        [int]$Seconds = 15
    )
    Write-Host "Checking $Name at $Url" -NoNewline
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Http $Url) {
            Write-Host ""
            Write-Host "$Name is ready." -ForegroundColor Green
            return
        }
        if ($null -ne $Process) {
            $Process.Refresh()
            if ($Process.HasExited) {
                Write-Host ""
                throw "$Name exited before its health check passed (exit code $($Process.ExitCode))."
            }
        }
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 1
    }
    Write-Host ""
    throw "$Name did not pass its health check within $Seconds seconds."
}

function Start-ManagedProcess {
    param(
        [string]$FilePath,
        [string]$Arguments,
        [string]$WorkingDirectory
    )
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $FilePath
    $startInfo.Arguments = $Arguments
    $startInfo.WorkingDirectory = $WorkingDirectory
    # Shell execution detaches long-running servers from this script's output
    # handles, so the caller can return after the health checks complete.
    $startInfo.UseShellExecute = $true
    $startInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    if (-not $process.Start()) {
        throw "Failed to start $FilePath"
    }
    return $process
}

& (Join-Path $PSScriptRoot "doctor.ps1")

$apiUrl = "http://127.0.0.1:8000/health"
$webUrl = "http://127.0.0.1:5173/"

if (-not (Test-Http $apiUrl)) {
    Write-Host "Starting QuestPilot API..."
    $python = Join-Path $backendDir ".venv\Scripts\python.exe"
    $apiProcess = Start-ManagedProcess `
        -FilePath $python `
        -Arguments "-m uvicorn questpilot.api.main:app --host 127.0.0.1 --port 8000" `
        -WorkingDirectory $backendDir
    Set-Content -LiteralPath (Join-Path $runtimeDir "api.pid") -Value $apiProcess.Id
}
else {
    Write-Host "Using the existing API. stop.ps1 will not stop an external process."
    $apiProcess = $null
}

if (-not (Test-Http $webUrl)) {
    Write-Host "Starting QuestPilot Web..."
    $node = (Get-Command node).Source
    $vite = Join-Path $frontendDir "node_modules\vite\bin\vite.js"
    $webProcess = Start-ManagedProcess `
        -FilePath $node `
        -Arguments "`"$vite`" --host 127.0.0.1 --port 5173 --strictPort" `
        -WorkingDirectory $frontendDir
    Set-Content -LiteralPath (Join-Path $runtimeDir "web.pid") -Value $webProcess.Id
}
else {
    Write-Host "Using the existing web server. stop.ps1 will not stop an external process."
    $webProcess = $null
}

Wait-Http -Name "QuestPilot API" -Url $apiUrl -Process $apiProcess
Wait-Http -Name "QuestPilot Web" -Url $webUrl -Process $webProcess

Write-Host ""
Write-Host "QuestPilot is running:" -ForegroundColor Cyan
Write-Host "  Web: http://127.0.0.1:5173/"
Write-Host "  API: http://127.0.0.1:8000/docs"
