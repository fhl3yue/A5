# 发行版打包说明

## 1. 推荐形态

低显卡设备优先使用“公网 HTTPS 云端服务 + Windows 轻量客户端 + Android WebView APK”：

- 云端 FastAPI 负责问答、知识库、TTS、ASR、数字人视频适配。
- 自有 GPU 主机运行外部数字人视频服务；AIGCPanel 只作为模型管理或验证工具，不进入发行包。
- Windows 客户端只打开云端页面，不打包后端、ASR、TTS、视频模型。
- Android APK 只加载游客端页面，权限只包含 `INTERNET` 和 `RECORD_AUDIO`。

## 2. 云端配置

在 `.env` 中配置数字人视频服务：

```dotenv
DIGITAL_VIDEO_ENABLED=true
DIGITAL_VIDEO_BASE_URL=https://gpu.example.com
DIGITAL_VIDEO_API_KEY=replace-with-token
DIGITAL_VIDEO_AVATAR_ID=default
DIGITAL_VIDEO_TIMEOUT_SECONDS=8
```

后端会请求：

```text
POST {DIGITAL_VIDEO_BASE_URL}/api/digital-video/generate
```

请求体：

```json
{
  "request_id": "uuid",
  "avatar_id": "default",
  "text": "数字人讲解文本",
  "audio_url": "/generated/audio/answer_xxx.mp3",
  "max_wait_seconds": 8
}
```

返回体：

```json
{
  "status": "ready",
  "video_url": "https://gpu.example.com/generated/video/answer_xxx.mp4",
  "message": "ok"
}
```

`status` 为 `ready` 且存在 `video_url` 时，游客端播放视频；`timeout`、`error` 或未启用时自动回退到音频和原 CSS 动效。

## 3. Windows 轻量客户端

构建：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_cloud_client.ps1
```

输出：

```text
dist\scenic-ai-guide-client
```

发布前编辑：

```text
dist\scenic-ai-guide-client\app-url.txt
```

写入云端地址，例如：

```text
https://your-domain.example/app/
```

用户双击 `scenic-ai-guide-client.exe` 后会打开默认浏览器访问该地址。

## 4. Android WebView APK 云构建

推荐在 GitHub Actions 中构建 APK，本机不需要安装 Android SDK 或 Gradle：

1. 推送代码到 GitHub。
2. 打开 Actions 页面的 `Build Android APK` workflow。
3. 点击 `Run workflow`。
4. 在 `app_url` 中输入公网 HTTPS 地址，例如 `https://your-domain.example/app/?client=android`。
5. 构建完成后下载 artifact：`scenic-ai-guide-debug-apk`。

默认产物为 debug 签名 APK，路径为：

```text
app-debug.apk
```

该 APK 可用于演示、测试和队友复现；正式分发前再配置 release keystore 并构建签名 release 包。

## 5. Android WebView APK 本地构建

配置：

```text
android-webview\app\src\main\res\values\strings.xml
```

把 `scenic_app_url` 改成：

```text
https://your-domain.example/app/?client=android
```

构建：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_android_webview.ps1
```

默认输出：

```text
android-webview\app\build\outputs\apk\debug\app-debug.apk
```

本地构建需要 JDK 17、Android SDK 和 Gradle；当前推荐优先使用 GitHub Actions 云构建。

## 6. 本地完整演示包

需要无云端环境演示时，可继续构建完整 Windows 后端包：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_demo.ps1
```

输出：

```text
dist\scenic-ai-guide-demo
```

该包仍会内置 FastAPI 后端、前端、样例数据和 Python 运行依赖，但不内置实时数字人视频模型。

## 7. 发布前检查

- `GET /api/health` 返回 `status: ok`。
- 文本问答返回 `audio_url`，开启数字人视频后返回 `video_status`。
- `video_status=ready` 时游客端播放视频；`timeout/error/disabled` 时自动回退音频。
- APK 可打开游客端、录音、问答和播放视频。
- 数字人形象素材必须为自制或已授权素材。

## 8. 本地 mock 数字人视频服务

需要先验证接口链路时，可启动 mock 服务：

```powershell
$env:MOCK_DIGITAL_VIDEO_API_KEY="dev-token"
$env:MOCK_DIGITAL_VIDEO_STATUS="ready"
python -m uvicorn mock_digital_video_service:app --host 127.0.0.1 --port 8020 --app-dir .\scripts
```

后端 `.env` 对应配置：

```dotenv
DIGITAL_VIDEO_ENABLED=true
DIGITAL_VIDEO_BASE_URL=http://127.0.0.1:8020
DIGITAL_VIDEO_API_KEY=dev-token
DIGITAL_VIDEO_AVATAR_ID=default
DIGITAL_VIDEO_TIMEOUT_SECONDS=8
```

`MOCK_DIGITAL_VIDEO_STATUS` 可设为 `ready`、`timeout`、`error`，用于验证前端回退逻辑。
