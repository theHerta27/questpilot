$ErrorActionPreference = "Stop"
$health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
if ($health.status -ne "ok") {
  throw "API health check failed"
}
Write-Host "QuestPilot API smoke check passed."
