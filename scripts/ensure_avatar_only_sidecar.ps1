param(
    [string]$BaseUrl = "http://127.0.0.1:18085",
    [string]$OpenAvatarRoot = "D:\OpenAvatarChatLab\OpenAvatarChat",
    [int]$Port = 18085,
    [double]$MaxAudioSeconds = 24,
    [switch]$Preload
)

$ErrorActionPreference = "Stop"
$base = $BaseUrl.TrimEnd("/")

function Test-HttpOk([string]$Url, [int]$TimeoutSec = 3) {
    try {
        Invoke-RestMethod -Method Get -Uri $Url -TimeoutSec $TimeoutSec | Out-Null
        return $true
    } catch {
        return $false
    }
}

if (Test-HttpOk "$base/health" 3) {
    Write-Host "LiteAvatar avatar-only sidecar is already ready: $base" -ForegroundColor Green
    exit 0
}

$StartScript = Join-Path $OpenAvatarRoot "run_a5_liteavatar_avatar_only.ps1"
if (-not (Test-Path -LiteralPath $StartScript)) {
    throw "LiteAvatar sidecar script not found: $StartScript"
}

$LogDir = Join-Path (Split-Path -Parent $PSScriptRoot) "data\generated\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogPath = Join-Path $LogDir "avatar_only_sidecar.log"

$ArgsText = "-Port $Port -MaxAudioSeconds $MaxAudioSeconds"
if ($Preload) {
    $ArgsText += " -Preload"
}

Write-Host "Starting LiteAvatar avatar-only sidecar: $base" -ForegroundColor Cyan
$Command = ". '$StartScript' $ArgsText *>&1 | Tee-Object -FilePath '$LogPath'"
Start-Process -FilePath powershell.exe `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $Command) `
    -WorkingDirectory $OpenAvatarRoot `
    -WindowStyle Hidden | Out-Null

for ($Attempt = 1; $Attempt -le 45; $Attempt++) {
    Start-Sleep -Seconds 1
    if (Test-HttpOk "$base/health" 2) {
        Write-Host "LiteAvatar avatar-only sidecar is ready: $base" -ForegroundColor Green
        exit 0
    }
}

throw "LiteAvatar sidecar did not become ready in time. Check log: $LogPath"
