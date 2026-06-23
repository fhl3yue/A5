param(
  [int]$Limit = 0,
  [switch]$SkipEvaluation,
  [switch]$SkipDemo
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
  $Python = "python"
}

$ArgsList = @((Join-Path $RepoRoot "scripts\prewarm_edge_tts_cache.py"))
if ($Limit -gt 0) {
  $ArgsList += @("--limit", "$Limit")
}
if ($SkipEvaluation) {
  $ArgsList += "--skip-evaluation"
}
if ($SkipDemo) {
  $ArgsList += "--skip-demo"
}

Set-Location $RepoRoot
& $Python @ArgsList
