# OpenAvatarChat / LiteAvatar 数字人接入说明

## 当前结论

本项目不再把完整 OpenAvatarChat 网页嵌入游客端。当前推荐路线是只抽离 LiteAvatar 的人物渲染能力，作为 `avatar-only sidecar` 独立运行：

```text
A5 问答/RAG -> A5 生成中文语音 -> LiteAvatar avatar-only sidecar -> MP4 真人数字人讲解 -> A5 游客端播放
```

这条路线不使用摄像头，不接管 A5 的 ASR、LLM、RAG、后台和 H5 页面，也不打开 OpenAvatarChat 自带聊天 UI。

## 为什么不直接用完整 8282 页面

完整 OpenAvatarChat 适合验证官方 Demo，但对当前项目太重：

- 它包含摄像头、RTC、ASR、LLM、前端 UI 等一整套链路。
- 这些能力和 A5 已经完成的 RAG/问答/语音/后台重复。
- 本机显存和系统稳定性压力较大，曾出现卡顿和死机风险。
- 直接 iframe 嵌入会像“平铺一个外部页面”，不是深度融合。

因此正式演示主线只保留 LiteAvatar 渲染核心：输入音频，输出会动、有口型的人物视频。

## 启动 LiteAvatar avatar-only sidecar

OpenAvatarChat 实验目录建议放在：

```text
D:\OpenAvatarChatLab\OpenAvatarChat
```

启动轻量数字人渲染服务：

```powershell
powershell -ExecutionPolicy Bypass -File D:\OpenAvatarChatLab\OpenAvatarChat\run_a5_liteavatar_avatar_only.ps1 -Preload
```

检查服务：

```powershell
powershell -ExecutionPolicy Bypass -File D:\software\scripts\check_avatar_only_sidecar.ps1 -Warmup
```

服务地址：

```text
http://127.0.0.1:18085
```

主要接口：

- `GET /health`
- `POST /warmup`
- `POST /avatar/speak`
- `GET /video/{filename}`

## A5 侧配置

在 `D:\software\.env` 中启用 avatar-only：

```env
AVATAR_ONLY_ENABLED=true
AVATAR_ONLY_BASE_URL=http://127.0.0.1:18085
AVATAR_ONLY_TIMEOUT_SECONDS=45
OPENAVATAR_ENABLED=false
```

说明：

- `AVATAR_ONLY_ENABLED=true` 后，游客端会优先请求服务端语音，以便驱动 LiteAvatar 生成视频。
- `OPENAVATAR_ENABLED=false` 表示不启用完整 8282 iframe。
- 如果 sidecar 没启动，A5 仍可正常文字问答和语音回退，不应崩溃。

## 性能策略

LiteAvatar 不是零成本组件，不能让游客每次等待完整冷启动视频。当前策略是：

- 启动时先 `-Preload` 或调用 `/warmup`，避免首次模型加载算进演示等待。
- sidecar 内部串行渲染，避免并发推理拖死电脑。
- 相同音频会命中视频缓存，重复演示可接近即时返回。
- A5 已有 Edge TTS 缓存，常见问题可提前预热音频。
- 文本回答仍先返回，数字人视频异步生成，失败时回退语音。

## 演示顺序建议

1. 启动 `avatar-only sidecar` 并预热。
2. 启动 A5 后端。
3. 打开 `http://127.0.0.1:8000/app/`。
4. 提问常见问题，例如“九龙灌浴几点开始表演？”
5. 先看到文字回答和语音状态，随后回答卡片出现“数字人讲解”。
6. 点击或等待自动播放，舞台区域播放 LiteAvatar 生成的真人讲解视频。

## 历史备用方案

完整 OpenAvatarChat `8282` iframe 只保留为实验记录，不建议作为答辩主路线。当前主线是 `18085 avatar-only sidecar`。
