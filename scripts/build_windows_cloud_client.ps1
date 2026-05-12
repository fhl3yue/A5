$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$DistRoot = Join-Path $RepoRoot "dist"
$PackageName = "scenic-ai-guide-client"
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
& $Python -m pip install "pyinstaller==6.20.0"

New-Item -ItemType Directory -Force -Path $DistRoot | Out-Null
if (Test-Path -LiteralPath $OutputDir) {
  Remove-Item -LiteralPath $OutputDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$BuildRoot = Join-Path $RepoRoot "build"
$PyInstallerWork = Join-Path $BuildRoot "pyinstaller-cloud-client"
New-Item -ItemType Directory -Force -Path $BuildRoot | Out-Null

& $Python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --name $PackageName `
  --distpath $OutputDir `
  --workpath $PyInstallerWork `
  --specpath $BuildRoot `
  "scripts\cloud_client_launcher.py"

$AppUrl = $env:SCENIC_AI_APP_URL
if (-not $AppUrl) {
  $AppUrl = "https://your-domain.example/app/"
}
Set-Content -LiteralPath (Join-Path $OutputDir "app-url.txt") -Value $AppUrl -Encoding UTF8

$Readme = @"
Scenic AI Guide Windows Client

1. Edit app-url.txt and replace it with your HTTPS cloud app URL.
2. Double-click scenic-ai-guide-client.exe.
3. The client opens the configured cloud app in the default browser.
"@
Set-Content -LiteralPath (Join-Path $OutputDir "README-client.txt") -Value $Readme -Encoding UTF8

Write-Host "Windows cloud client created: $OutputDir" -ForegroundColor Green
Write-Host "Configure URL in: $OutputDir\app-url.txt" -ForegroundColor Green
