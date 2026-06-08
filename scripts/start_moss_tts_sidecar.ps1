param(
  [int]$Port = 18083,
  [string]$ExecutionProvider = "cpu",
  [int]$CpuThreads = 0,
  [int]$MaxNewFrames = 240,
  [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$SidecarRoot = Join-Path $RepoRoot "local_tts"
$MossRoot = Join-Path $SidecarRoot "MOSS-TTS-Nano"
$VenvRoot = Join-Path $RepoRoot ".venv_tts"
$VenvPython = Join-Path $VenvRoot "Scripts\python.exe"

Set-Location $RepoRoot

if (-not (Test-Path $MossRoot)) {
  New-Item -ItemType Directory -Force -Path $SidecarRoot | Out-Null
  Write-Host "Cloning MOSS-TTS-Nano into $MossRoot" -ForegroundColor Cyan
  git clone --depth 1 https://github.com/OpenMOSS/MOSS-TTS-Nano.git $MossRoot
}

if (-not (Test-Path $VenvPython)) {
  Write-Host "Creating isolated TTS virtual environment at $VenvRoot" -ForegroundColor Cyan
  $PyLauncher = Get-Command py -ErrorAction SilentlyContinue
  if ($PyLauncher) {
    & py -3.12 -m venv $VenvRoot
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VenvPython)) {
      Write-Host "Python 3.12 was not available through py launcher; falling back to default python." -ForegroundColor Yellow
      python -m venv $VenvRoot
    }
  } else {
    python -m venv $VenvRoot
  }
}

if (-not $SkipInstall) {
  Write-Host "Installing MOSS-TTS-Nano dependencies. This can take a while on first run." -ForegroundColor Cyan
  & $VenvPython -m pip install --upgrade pip
  & $VenvPython -m pip install -r (Join-Path $MossRoot "requirements.txt")
  & $VenvPython -m pip install -e $MossRoot
}

$ArgsList = @(
  (Join-Path $MossRoot "app_onnx.py"),
  "--host", "127.0.0.1",
  "--port", "$Port",
  "--execution-provider", $ExecutionProvider,
  "--max-new-frames", "$MaxNewFrames"
)

if ($CpuThreads -gt 0) {
  $ArgsList += @("--cpu-threads", "$CpuThreads")
}

Write-Host "Starting MOSS-TTS-Nano ONNX sidecar on http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host "Use LOCAL_TTS_ENABLED=true and LOCAL_TTS_BASE_URL=http://127.0.0.1:$Port in .env after the sidecar is ready." -ForegroundColor Yellow
Set-Location $MossRoot
& $VenvPython @ArgsList
