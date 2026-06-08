param(
  [string]$BaseUrl = "http://127.0.0.1:18083",
  [string]$DemoId = "demo-1",
  [string]$Text = "Welcome to Lingshan Scenic Area."
)

$ErrorActionPreference = "Stop"

$BaseUrl = $BaseUrl.TrimEnd("/")

Write-Host "Checking local TTS sidecar health: $BaseUrl/health" -ForegroundColor Cyan
$Health = Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get -TimeoutSec 5
$Health | ConvertTo-Json -Depth 4

Write-Host "Requesting one short synthesis from $BaseUrl/api/generate" -ForegroundColor Cyan
$Body = @{
  text = $Text
  demo_id = $DemoId
  max_new_frames = "120"
  voice_clone_max_text_tokens = "75"
  enable_text_normalization = "1"
  enable_normalize_tts_text = "1"
  cpu_threads = "0"
  attn_implementation = "fixed"
  do_sample = "1"
  seed = "0"
}

$Started = Get-Date
$Result = Invoke-RestMethod -Uri "$BaseUrl/api/generate" -Method Post -Body $Body -TimeoutSec 30
$Elapsed = ((Get-Date) - $Started).TotalSeconds
$AudioLength = if ($Result.audio_base64) { $Result.audio_base64.Length } else { 0 }

[pscustomobject]@{
  ok = $AudioLength -gt 0
  elapsed_seconds = [math]::Round($Elapsed, 3)
  audio_base64_length = $AudioLength
  sample_rate = $Result.sample_rate
  run_status = $Result.run_status
} | ConvertTo-Json -Depth 4
