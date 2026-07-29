$ErrorActionPreference = "Stop"

Write-Host "QuestPilot development setup"
Write-Host "1. Copy .env.example to .env and set DATABASE_URL if PostgreSQL is available."
Write-Host "2. Backend: cd backend; uv sync --extra dev; uv run questpilot-seed; uv run questpilot-api"
Write-Host "3. Frontend: cd frontend; npm install; npm run dev"
