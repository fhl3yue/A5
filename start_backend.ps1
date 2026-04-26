$ErrorActionPreference = "Stop"

Set-Location "D:\software"

if (-not (Test-Path ".venv\Scripts\python.exe")) {
  python -m venv .venv
}

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env" -Force
}

$env:PYTHONPATH = "D:\software\backend"

& "D:\software\.venv\Scripts\python.exe" "D:\software\scripts\init_db.py"
& "D:\software\.venv\Scripts\python.exe" "D:\software\scripts\import_sample_data.py"

Write-Host "Starting backend on http://127.0.0.1:8000" -ForegroundColor Green
& "D:\software\.venv\Scripts\uvicorn.exe" app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir "D:\software\backend"

