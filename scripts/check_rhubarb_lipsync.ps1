param(
  [string]$RhubarbPath = "tools\rhubarb\rhubarb.exe"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ResolvedPath = Join-Path $RepoRoot $RhubarbPath

Write-Host "Rhubarb Lip Sync check"
Write-Host "Repo: $RepoRoot"
Write-Host "Expected binary: $ResolvedPath"

if (-not (Test-Path $ResolvedPath)) {
  Write-Host "Status: missing"
  Write-Host "Put rhubarb.exe under tools\rhubarb\, then set ENABLE_RHUBARB_LIPSYNC=true in .env."
  exit 1
}

Write-Host "Status: found"
try {
  & $ResolvedPath "--help" | Select-Object -First 5
  Write-Host "Rhubarb executable can be launched."
} catch {
  Write-Host "Rhubarb executable exists but failed to launch: $($_.Exception.Message)"
  exit 1
}
