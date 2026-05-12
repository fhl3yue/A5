param(
  [switch]$Full
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

$BackendDir = Join-Path $RepoRoot "backend"
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$ResetScript = Join-Path $RepoRoot "scripts\reset_demo_data.py"
$env:PYTHONPATH = $BackendDir

if ($Full) {
  & $Python $ResetScript --full
} else {
  & $Python $ResetScript
}

Write-Host "Demo environment reset completed." -ForegroundColor Green
