param(
  [switch]$Reload,
  [switch]$SkipAvatarOnly
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

function Get-DotEnvValue([string]$Key, [string]$DefaultValue) {
  $EnvPath = Join-Path $RepoRoot ".env"
  if (-not (Test-Path -LiteralPath $EnvPath)) {
    return $DefaultValue
  }
  $Line = Get-Content -LiteralPath $EnvPath -Encoding UTF8 |
    Where-Object { $_ -match "^$Key=" } |
    Select-Object -First 1
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

function Test-HttpOk([string]$Url, [int]$TimeoutSec = 3) {
  try {
    Invoke-RestMethod -Method Get -Uri $Url -TimeoutSec $TimeoutSec | Out-Null
    return $true
  } catch {
    return $false
  }
}

function Ensure-AvatarOnlySidecar {
  $Enabled = (Get-DotEnvValue "AVATAR_ONLY_ENABLED" "false").ToLowerInvariant()
  if ($SkipAvatarOnly -or $Enabled -ne "true") {
    return
  }

  $BaseUrl = (Get-DotEnvValue "AVATAR_ONLY_BASE_URL" "http://127.0.0.1:18085").TrimEnd("/")
  if (Test-HttpOk "$BaseUrl/health" 3) {
    Write-Host "LiteAvatar avatar-only sidecar is ready: $BaseUrl" -ForegroundColor Green
    return
  }

  $OpenAvatarRoot = Get-DotEnvValue "OPENAVATAR_ROOT" "D:\OpenAvatarChatLab\OpenAvatarChat"
  $StartScript = Join-Path $OpenAvatarRoot "run_a5_liteavatar_avatar_only.ps1"
  if (-not (Test-Path -LiteralPath $StartScript)) {
    Write-Host "LiteAvatar sidecar script not found: $StartScript" -ForegroundColor Yellow
    Write-Host "A5 backend will still start, but avatar video will be unavailable." -ForegroundColor Yellow
    return
  }

  $Port = 18085
  try {
    $Uri = [Uri]$BaseUrl
    if ($Uri.Port -gt 0) {
      $Port = $Uri.Port
    }
  } catch {
    Write-Host "Invalid AVATAR_ONLY_BASE_URL=$BaseUrl, using default port 18085." -ForegroundColor Yellow
  }

  $LogDir = Join-Path $RepoRoot "data\generated\logs"
  New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
  $LogPath = Join-Path $LogDir "avatar_only_sidecar.log"

  Write-Host "Starting LiteAvatar avatar-only sidecar on $BaseUrl ..." -ForegroundColor Cyan
  $Command = ". '$StartScript' -Port $Port -Preload *>&1 | Tee-Object -FilePath '$LogPath'"
  Start-Process -FilePath powershell.exe `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $Command) `
    -WorkingDirectory $OpenAvatarRoot `
    -WindowStyle Hidden | Out-Null

  for ($Attempt = 1; $Attempt -le 45; $Attempt++) {
    Start-Sleep -Seconds 1
    if (Test-HttpOk "$BaseUrl/health" 2) {
      Write-Host "LiteAvatar avatar-only sidecar is ready: $BaseUrl" -ForegroundColor Green
      return
    }
  }

  Write-Host "LiteAvatar sidecar did not become ready in time. Check: $LogPath" -ForegroundColor Yellow
  Write-Host "A5 backend will continue; text/audio remain available, avatar video will fall back." -ForegroundColor Yellow
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

Ensure-AvatarOnlySidecar
Stop-ProjectListeners $Port

Write-Host "Starting backend on http://127.0.0.1:$Port" -ForegroundColor Green
if ($Reload) {
  & $Python (Join-Path $RepoRoot "scripts\init_db.py")
  & $Python (Join-Path $RepoRoot "scripts\import_sample_data.py")
  & $Uvicorn app.main:app --host $HostName --port $Port --reload --app-dir $BackendDir
} else {
  & $Python -m app.launcher
}
