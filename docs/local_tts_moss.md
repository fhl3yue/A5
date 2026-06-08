# 本地中文 TTS 回退配置说明

本文档说明如何把服务端异步语音回退从 Edge TTS 优先改为本地 MOSS-TTS-Nano ONNX 优先。游客端浏览器本地朗读仍然是第一选择；本地 TTS 只用于手机、WebView、本地朗读失败或强制 `server_only` 的场景。

## 1. 启动 MOSS-TTS-Nano ONNX Sidecar

首次启动会克隆 MOSS-TTS-Nano，并在项目根目录创建独立 `.venv_tts`，不会污染主项目 `.venv`。

```powershell
Set-Location D:\software
powershell -ExecutionPolicy Bypass -File .\scripts\start_moss_tts_sidecar.ps1
```

如果依赖已经安装过，可以跳过安装步骤：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_moss_tts_sidecar.ps1 -SkipInstall
```

启动成功后，MOSS 服务默认位于：

```text
http://127.0.0.1:18083
```

## 2. 检测本地 TTS 服务

另开一个 PowerShell 窗口运行：

```powershell
Set-Location D:\software
powershell -ExecutionPolicy Bypass -File .\scripts\check_local_tts_provider.ps1
```

如果返回 `ok=true` 且 `audio_base64_length` 大于 0，说明本地 TTS 服务可用。

## 3. 启用后端本地 TTS 回退

在 `D:\software\.env` 中加入或修改：

```dotenv
SERVER_TTS_PROVIDER=auto
LOCAL_TTS_ENABLED=true
LOCAL_TTS_PROVIDER=moss_onnx
LOCAL_TTS_BASE_URL=http://127.0.0.1:18083
LOCAL_TTS_TIMEOUT_SECONDS=8
LOCAL_TTS_DEMO_ID=demo-1
LOCAL_TTS_MAX_NEW_FRAMES=240
LOCAL_TTS_VOICE_CLONE_MAX_TEXT_TOKENS=75
LOCAL_TTS_CPU_THREADS=0
```

然后重启后端：

```powershell
powershell -ExecutionPolicy Bypass -File .\start_backend.ps1
```

## 4. 验证后端链路

强制服务端生成音频：

```powershell
$body = @{
  question = "九龙灌浴几点开始表演"
  user_id = "tts-check"
  tts_mode = "server_only"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/chat/text" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body $body
```

再用返回的 `log_id` 轮询：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/chat/audio/<log_id>"
```

管理端状态接口也会显示本地 TTS 状态：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/admin/ai/status"
```

## 5. 回退逻辑

- `SERVER_TTS_PROVIDER=auto`：先试本地 MOSS ONNX，失败后自动回退 Edge TTS。
- `SERVER_TTS_PROVIDER=local`：只试本地 MOSS ONNX，失败则音频状态为 failed。
- `SERVER_TTS_PROVIDER=edge`：只使用 Edge TTS。

模型权重、`.venv_tts`、`local_tts` 和生成音频都不会进入 Git。
