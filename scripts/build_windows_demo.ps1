$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$DistRoot = Join-Path $RepoRoot "dist"
$PackageName = "scenic-ai-guide-demo"
$OutputDir = Join-Path $DistRoot $PackageName

$ResolvedDistRoot = [System.IO.Path]::GetFullPath($DistRoot)
$ResolvedOutputDir = [System.IO.Path]::GetFullPath($OutputDir)
$ResolvedDistRootWithSeparator = $ResolvedDistRoot.TrimEnd("\") + "\"
if (
  $ResolvedOutputDir -ne $ResolvedDistRoot -and
  -not $ResolvedOutputDir.StartsWith($ResolvedDistRootWithSeparator, [System.StringComparison]::OrdinalIgnoreCase)
) {
  throw "OutputDir must be inside $ResolvedDistRoot"
}

Set-Location $RepoRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
  python -m venv .venv
}

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
& $Python -m pip install -r "backend\requirements.txt"
& $Python -m pip install "pyinstaller==6.20.0"

New-Item -ItemType Directory -Force -Path $DistRoot | Out-Null
if (Test-Path -LiteralPath $ResolvedOutputDir) {
  Remove-Item -LiteralPath $ResolvedOutputDir -Recurse -Force
}

$BuildRoot = Join-Path $RepoRoot "build"
$PyInstallerWork = Join-Path $BuildRoot "pyinstaller"
New-Item -ItemType Directory -Force -Path $BuildRoot | Out-Null

& $Python -m PyInstaller `
  --noconfirm `
  --clean `
  --onedir `
  --name $PackageName `
  --distpath $DistRoot `
  --workpath $PyInstallerWork `
  --specpath $BuildRoot `
  --paths (Join-Path $RepoRoot "backend") `
  --collect-all "edge_tts" `
  --collect-submodules "faster_whisper" `
  --collect-submodules "ctranslate2" `
  --hidden-import "multipart" `
  "backend\app\launcher.py"

$PackageDir = Join-Path $DistRoot $PackageName
New-Item -ItemType Directory -Force -Path (Join-Path $PackageDir "data\sample") | Out-Null
Copy-Item -LiteralPath (Join-Path $RepoRoot "frontend") -Destination (Join-Path $PackageDir "frontend") -Recurse -Force
Copy-Item -Path (Join-Path $RepoRoot "data\sample\*") -Destination (Join-Path $PackageDir "data\sample") -Recurse -Force
Copy-Item -LiteralPath (Join-Path $RepoRoot ".env.example") -Destination (Join-Path $PackageDir ".env") -Force
Copy-Item -LiteralPath (Join-Path $RepoRoot "README.md") -Destination (Join-Path $PackageDir "README.md") -Force

$StartScript = @'
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$env:SCENIC_AI_BASE_DIR = $Root
& "$Root\scenic-ai-guide-demo.exe"
'@
Set-Content -LiteralPath (Join-Path $PackageDir "start_demo.ps1") -Value $StartScript -Encoding UTF8

Write-Host "Windows demo package created: $PackageDir" -ForegroundColor Green
Write-Host "Run: powershell -ExecutionPolicy Bypass -File $PackageDir\start_demo.ps1" -ForegroundColor Green
