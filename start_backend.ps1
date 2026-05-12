$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
  python -m venv .venv
}

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env" -Force
}

$BackendDir = Join-Path $RepoRoot "backend"
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Uvicorn = Join-Path $RepoRoot ".venv\Scripts\uvicorn.exe"
$env:PYTHONPATH = $BackendDir

& $Python (Join-Path $RepoRoot "scripts\init_db.py")
& $Python (Join-Path $RepoRoot "scripts\import_sample_data.py")

Write-Host "Starting backend on http://127.0.0.1:8000" -ForegroundColor Green
& $Uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir $BackendDir
