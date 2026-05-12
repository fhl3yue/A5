$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$AndroidDir = Join-Path $RepoRoot "android-webview"
$Task = $env:ANDROID_BUILD_TASK
if (-not $Task) {
  $Task = ":app:assembleDebug"
}

$GradleCommand = Get-Command "gradle" -ErrorAction SilentlyContinue
if (-not (Test-Path (Join-Path $AndroidDir "gradlew.bat")) -and -not $GradleCommand) {
  throw "Gradle not found. Install Android Studio or Gradle, then rerun this script. Required: JDK 17, Android SDK, Gradle or Gradle Wrapper."
}

Set-Location $AndroidDir

if (Test-Path ".\gradlew.bat") {
  & ".\gradlew.bat" $Task
} else {
  & "gradle" $Task
}

Write-Host "Android build finished. Default debug APK: $AndroidDir\app\build\outputs\apk\debug\app-debug.apk" -ForegroundColor Green
