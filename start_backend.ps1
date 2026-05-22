param(
  [switch]$Reload
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

function Get-DotEnvValue([string]$Key, [string]$DefaultValue) {
  $EnvPath = Join-Path $RepoRoot ".env"
  if (-not (Test-Path $EnvPath)) {
    return $DefaultValue
  }
  $Line = Get-Content $EnvPath | Where-Object { $_ -match "^$Key=" } | Select-Object -First 1
  if (-not $Line) {
    return $DefaultValue
  }
  return ($Line -split "=", 2)[1].Trim()
}

function Stop-ProjectListeners([int]$Port) {
  $Connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  if (-not $Connections) {
    return
  }

  $ProcessIds = $Connections | Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($ProcessId in $ProcessIds) {
    $ProcessInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    $CommandLine = $ProcessInfo.CommandLine
    $IsProjectBackend = (
      $CommandLine -like "*$RepoRoot*" -or
      ($CommandLine -like "*uvicorn*" -and $CommandLine -like "*app.main*") -or
      ($CommandLine -like "*-m app.launcher*")
    )
    if ($IsProjectBackend) {
      Write-Host "Stopping old backend process PID $ProcessId on port $Port" -ForegroundColor Yellow
      Stop-Process -Id $ProcessId -Force
      Start-Sleep -Milliseconds 500
      continue
    }
    throw "Port $Port is occupied by PID $ProcessId and does not look like this project backend. Close it or change APP_PORT in .env."
  }
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
  python -m venv .venv
}

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env" -Force
}

$BackendDir = Join-Path $RepoRoot "backend"
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Uvicorn = Join-Path $RepoRoot ".venv\Scripts\uvicorn.exe"
$Port = [int](Get-DotEnvValue "APP_PORT" "8000")
$HostName = Get-DotEnvValue "APP_HOST" "0.0.0.0"
$env:PYTHONPATH = $BackendDir
$env:SCENIC_AI_BASE_DIR = $RepoRoot

Stop-ProjectListeners $Port

Write-Host "Starting backend on http://127.0.0.1:$Port" -ForegroundColor Green
if ($Reload) {
  & $Python (Join-Path $RepoRoot "scripts\init_db.py")
  & $Python (Join-Path $RepoRoot "scripts\import_sample_data.py")
  & $Uvicorn app.main:app --host $HostName --port $Port --reload --app-dir $BackendDir
} else {
  & $Python -m app.launcher
}
