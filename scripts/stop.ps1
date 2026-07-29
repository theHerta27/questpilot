$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runtimeDir = Join-Path $projectRoot ".runtime"

function Stop-ManagedProcess {
    param([string]$Name, [string]$PidFile)
    if (-not (Test-Path -LiteralPath $PidFile)) {
        Write-Host "$Name has no PID managed by start.ps1."
        return
    }
    $rawProcessId = (Get-Content -LiteralPath $PidFile -Raw).Trim()
    $processId = 0
    if (-not [int]::TryParse($rawProcessId, [ref]$processId) -or $processId -le 0) {
        Write-Host "$Name had an invalid PID file; removing it."
        Remove-Item -LiteralPath $PidFile -Force
        return
    }
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($process) {
        try {
            $process.Kill()
            $process.WaitForExit(5000) | Out-Null
            Write-Host "$Name stopped (PID $processId)." -ForegroundColor Green
        }
        catch {
            Write-Host "$Name could not be stopped through its stale process handle; checking again."
            if (Get-Process -Id $processId -ErrorAction SilentlyContinue) {
                throw
            }
        }
    }
    else {
        Write-Host "$Name was already stopped."
    }
    Remove-Item -LiteralPath $PidFile -Force
}

Stop-ManagedProcess "QuestPilot API" (Join-Path $runtimeDir "api.pid")
Stop-ManagedProcess "QuestPilot Web" (Join-Path $runtimeDir "web.pid")
