# Scenic AI Guide A-side Workspace

This workspace contains the A-side backend for the Scenic AI Guide competition project.

## Current scope

- FastAPI backend scaffold
- SQLite database models
- Scenic knowledge import scripts
- Text chat API
- Route recommendation API
- Feedback, logs, dashboard APIs
- Demo data reset script
- TTS audio URL generation
- Frontend handoff API docs
- Built-in visitor/admin web frontend

## Quick start

Read [docs/backend_setup.md](docs/backend_setup.md).
For release packaging, read [docs/release_packaging.md](docs/release_packaging.md).

## Portable local start

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r backend\requirements.txt
powershell -ExecutionPolicy Bypass -File .\start_backend.ps1
```

## Low-device clients

- Windows cloud client: `powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_cloud_client.ps1`
- Android WebView APK: run GitHub Actions workflow `Build Android APK`; local fallback is `powershell -ExecutionPolicy Bypass -File .\scripts\build_android_webview.ps1`

After startup, open:

- Web app: http://127.0.0.1:8000/app/
- API docs: http://127.0.0.1:8000/docs
