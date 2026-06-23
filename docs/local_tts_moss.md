# 本地中文 TTS 与 Edge 缓存配置说明

本文档说明当前项目的中文语音策略：游客端优先使用浏览器本地朗读；当手机、WebView、本地朗读失败或强制 `server_only` 时，后端再生成服务端音频。服务端音频先以 Edge TTS 缓存作为稳定主展示方案，MOSS-TTS-Nano ONNX 作为并行试验方案。

## 1. 当前推荐策略

推荐答辩和日常演示使用：

```dotenv
SERVER_TTS_PROVIDER=auto
LOCAL_TTS_ENABLED=false
EDGE_TTS_CACHE_ENABLED=true
EDGE_TTS_CACHE_MAX_ITEMS=300
EDGE_TTS_CACHE_VERSION=v1
```

含义如下：

- 桌面浏览器优先使用 `speechSynthesis` 本地朗读，首答最快。
- 服务端需要 MP3 时，优先命中 Edge TTS 缓存。
- 缓存未命中时再调用 Edge TTS 生成 MP3，并把结果写入缓存。
- MOSS 默认不启用，避免试验依赖影响主展示。

## 2. Edge TTS 缓存预热

答辩前建议先预热常见问题音频：

```powershell
Set-Location D:\software
powershell -ExecutionPolicy Bypass -File .\scripts\prewarm_edge_tts_cache.ps1
```

快速试跑前 3 条：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\prewarm_edge_tts_cache.ps1 -Limit 3
```

预热脚本会：

- 读取 50 题评测集和常见演示问题。
- 生成标准文本回答。
- 强制使用 Edge TTS 写入缓存。
- 输出缓存命中数、生成数、失败数和总耗时。
- 删除脚本生成的临时问答日志，避免污染游客统计。

缓存文件位于：

```text
D:\software\data\generated\audio\cache
```

该目录属于运行时生成内容，不进入 Git。

## 3. 为什么缓存不会串音色

Edge 缓存键由以下内容共同计算：

```text
回答文本 + voice_name + TTS_MAX_CHARS + edge_tts + EDGE_TTS_CACHE_VERSION
```

因此如果切换 `TTS_VOICE` 或后台数字人音色，系统不会误用旧音频。若希望主动废弃全部旧缓存，可以修改：

```dotenv
EDGE_TTS_CACHE_VERSION=v2
```

然后重新运行预热脚本。

## 4. 启动 MOSS-TTS-Nano ONNX Sidecar

MOSS 是可选试验方案。首次启动会克隆 MOSS-TTS-Nano，并在项目根目录创建独立 `.venv_tts`，不会污染主项目 `.venv`。

```powershell
Set-Location D:\software
powershell -ExecutionPolicy Bypass -File .\scripts\start_moss_tts_sidecar.ps1
```

如果依赖已经安装过，可以跳过安装：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_moss_tts_sidecar.ps1 -SkipInstall
```

默认服务地址：

```text
http://127.0.0.1:18083
```

## 5. 检测 MOSS 本地 TTS

另开一个 PowerShell 窗口运行：

```powershell
Set-Location D:\software
powershell -ExecutionPolicy Bypass -File .\scripts\check_local_tts_provider.ps1
```

如果返回 `ok=true` 且 `audio_base64_length` 大于 0，说明本地 TTS 服务可用。建议关注 `elapsed_seconds`：如果短回答稳定小于 5 秒，再考虑启用 MOSS。

## 6. 启用 MOSS 作为服务端优先回退

只有在 MOSS 检测稳定后，再修改本机 `.env`：

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

## 7. 验证服务端语音链路

强制服务端生成音频：

```powershell
$body = @{
  question = "九龙灌浴几点开始表演？"
  user_id = "tts-check"
  tts_mode = "server_only"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/chat/text" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body $body
```

用返回的 `log_id` 查询音频状态：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/chat/audio/<log_id>"
```

管理端状态接口也会显示服务端 TTS 状态：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/admin/ai/status"
```

重点查看：

- `server_tts_last_provider=edge_tts_cache` 表示命中 Edge 缓存。
- `server_tts_last_provider=edge_tts` 表示本次新生成 Edge MP3。
- `server_tts_last_provider=local_moss_onnx` 表示 MOSS 本地生成成功。
- `edge_tts_cache_items` 表示当前缓存音频数量。

## 8. 回退逻辑

- `SERVER_TTS_PROVIDER=auto`：启用 MOSS 时先试 MOSS，失败后回退 Edge TTS；未启用 MOSS 时直接走 Edge TTS/缓存。
- `SERVER_TTS_PROVIDER=local`：只试 MOSS，失败则音频状态为 `failed`。
- `SERVER_TTS_PROVIDER=edge`：只使用 Edge TTS/缓存。

模型权重、`.venv_tts`、`local_tts`、生成音频和 `.env` 都不提交 Git。

## 9. 当前本机 MOSS 试验结论

2026-06-08 本机已完成一次 MOSS 并行试验：

- 依赖安装阶段：`WeTextProcessing -> pynini` 在 Windows MSVC 下编译失败，因此默认文本规范化不可用。
- 模型下载阶段：官方 HuggingFace 连接超时，改用 `HF_ENDPOINT=https://hf-mirror.com` 后完成 ONNX 模型下载。
- 临时试验补丁：在忽略目录 `local_tts/MOSS-TTS-Nano` 内关闭 WeText 预加载后，MOSS sidecar 可启动，`/health` 返回正常。
- 生成结果：短中文“欢迎来到灵山胜境。”可生成音频，但 3 次耗时约 `16.65s / 16.92s / 16.64s`；降帧参数最快仍约 `13.56s`。
- 结论：当前本机 CPU 下 MOSS 不满足“服务端语音回退小于 5 秒”的升级条件，因此不启用 `LOCAL_TTS_ENABLED=true`，主展示继续使用浏览器本地朗读 + Edge TTS 缓存。

答辩时可说明：MOSS 属于并行探索的本地轻量 TTS 方案，已验证当前机器上速度不达标，所以系统采用更稳定的 Edge 缓存方案保证展示体验。
