param(
  [switch]$Full
)

$ErrorActionPreference = "Stop"

Set-Location "D:\software"
$env:PYTHONPATH = "D:\software\backend"

if ($Full) {
  & "D:\software\.venv\Scripts\python.exe" "D:\software\scripts\reset_demo_data.py" --full
} else {
  & "D:\software\.venv\Scripts\python.exe" "D:\software\scripts\reset_demo_data.py"
}

Write-Host "Demo environment reset completed." -ForegroundColor Green
