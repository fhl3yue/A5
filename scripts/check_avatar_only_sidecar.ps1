param(
    [string]$BaseUrl = "http://127.0.0.1:18085",
    [switch]$Warmup
)

$ErrorActionPreference = "Stop"
$base = $BaseUrl.TrimEnd("/")

Write-Host "Checking LiteAvatar avatar-only sidecar: $base"

try {
    $health = Invoke-RestMethod -Method Get -Uri "$base/health" -TimeoutSec 5
} catch {
    Write-Host "avatar-only sidecar is not reachable." -ForegroundColor Red
    Write-Host "Start it with:" -ForegroundColor Yellow
    Write-Host "powershell -ExecutionPolicy Bypass -File D:\OpenAvatarChatLab\OpenAvatarChat\run_a5_liteavatar_avatar_only.ps1 -Preload"
    throw
}

Write-Host "Provider: $($health.provider)"
Write-Host "Loaded:   $($health.loaded)"
Write-Host "FPS:      $($health.fps)"
Write-Host "GPU:      $($health.use_gpu)"

if ($Warmup) {
    Write-Host "Warming up LiteAvatar model..."
    $warmupResult = Invoke-RestMethod -Method Post -Uri "$base/warmup" -TimeoutSec 90
    Write-Host "Warmup ok: $($warmupResult.ok), elapsed: $($warmupResult.elapsed_seconds)s"
}

Write-Host "avatar-only sidecar check finished." -ForegroundColor Green
