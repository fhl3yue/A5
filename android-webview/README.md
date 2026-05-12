# Android WebView APK

This project builds the low-device Android client for Scenic AI Guide. It loads the cloud visitor app in a WebView and only requests `INTERNET` and `RECORD_AUDIO`.

## Configure

Edit `app/src/main/res/values/strings.xml`:

```xml
<string name="scenic_app_url">https://your-domain.example/app/?client=android</string>
```

Use a public HTTPS URL for microphone permission and production WebView compatibility.

## Cloud Build

Use GitHub Actions when the local machine does not have Android SDK or Gradle:

1. Open `Actions`.
2. Run `Build Android APK`.
3. Set `app_url` to the public HTTPS visitor URL.
4. Download the `scenic-ai-guide-debug-apk` artifact.

The first APK uses Android debug signing for demos and teammate reproduction.

## Local Build

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_android_webview.ps1
```

Default output:

```text
android-webview\app\build\outputs\apk\debug\app-debug.apk
```

Build prerequisites:

- JDK 17
- Android Studio or Android SDK command-line tools
- Gradle or a Gradle Wrapper
