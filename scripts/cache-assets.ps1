$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backendRoot = Join-Path $projectRoot "backend"
Push-Location $backendRoot
try {
    $env:UV_CACHE_DIR = ".uv-cache"
    uv run --offline python -m questpilot.asset_cache
}
finally {
    Pop-Location
}
