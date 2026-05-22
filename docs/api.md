# A端接口文档

## 1. 基础信息

- 服务地址：`http://127.0.0.1:8000`
- Swagger：`http://127.0.0.1:8000/docs`
- 返回格式：统一为 `{ code, message, data }`

## 2. 文本问答

- 地址：`POST /api/chat/text`
- 请求体：

```json
{
  "question": "九龙灌浴几点开始",
  "user_id": "U0001"
}
```

- 返回体：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "log_id": 1,
    "transcript": "九龙灌浴几点开始表演",
    "interpreted_question": "九龙灌浴几点开始表演？",
    "answer": "根据当前景区知识库，...",
    "audio_url": "/generated/audio/answer_xxx.mp3",
    "english_available": false,
    "answer_source": "rag_model",
    "model_name": "GLM-5.1",
    "lipsync_available": true,
    "video_url": "https://gpu.example.com/generated/video/answer_xxx.mp4",
    "video_status": "ready",
    "emotion": "neutral",
    "reference": ["九龙灌浴"],
    "response_seconds": 0.182
  }
}
```

## 3. 语音问答

- 地址：`POST /api/chat/voice`
- 表单参数：
  - `transcript`: 可选，前端转写文本
  - `user_id`: 可选
  - `file`: 可选，音频文件

说明：
- 当前版本已接入本地 ASR，可直接上传音频文件
- 若前端自己先完成转写，也可以继续传 `transcript`
- 返回中的 `transcript` 是原始识别文本，`interpreted_question` 是后端提炼后的最终检索问题
- 文本问答与语音问答在成功时都会尽量返回 `audio_url`
- `english_available=true` 表示游客端当前回答可点击 `English`，并调用独立英文回答服务
- 开启数字人视频服务后会返回 `video_url` 和 `video_status`；`ready` 播放视频，`timeout/error/disabled` 回退音频

## 4. 英文回答

- 地址：`POST /api/chat/translate`
- 请求体：

```json
{
  "log_id": 1,
  "text": "如果你计划在灵山胜境游览半天，建议走“灵山大照壁 → 祥符禅寺 → 灵山大佛 → 灵山梵宫”。",
  "target_language": "en"
}
```

- 返回体：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "log_id": 1,
    "target_language": "en",
    "translation": "If you only have half a day at Lingshan Scenic Area, a recommended route is ...",
    "audio_url": "/generated/audio/answer_xxx.mp3"
  }
}
```

说明：

- 英文回答服务使用独立的 OpenAI 兼容配置，不复用中文主问答模型配置
- 若只配置英文模型，未配置英文 TTS，则 `audio_url` 返回 `null`
- 若未配置英文服务，接口返回 `503`

## 5. 路线推荐

- 地址：`POST /api/recommend/route`
- 请求体：

```json
{
  "interest": "历史文化",
  "duration": "半天",
  "user_id": "web-visitor"
}
```

- 返回体：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "route_name": "历史文化半日路线",
    "route_spots": ["灵山大照壁", "祥符禅寺", "灵山大佛"],
    "reason": "结合当前输入与历史偏好生成路线。",
    "matched_interest": "历史文化",
    "personalization_basis": ["当前输入：历史文化", "游览时长：半天"]
  }
}
```

## 6. 满意度反馈

- 地址：`POST /api/feedback`
- 请求体：

```json
{
  "log_id": 1,
  "satisfaction": 5
}
```

## 7. 管理员登录

- 地址：`POST /api/admin/login`

## 8. 问答日志

- 地址：`GET /api/admin/logs?limit=50`

## 9. 数据看板

- 地址：`GET /api/admin/dashboard`
- 用途：展示当日服务数据、热门问题、情绪分布、本周服务趋势和满意度趋势

## 10. 游客感受度报告

- 地址：`GET /api/admin/visitor-report`
- 用途：根据交互日志生成游客关注点、七日情绪趋势和服务建议
- 返回体：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "summary": "已分析 20 条游客互动记录，满意度为 80%。当前主要情绪为 neutral，平均响应耗时 0.31 秒。",
    "focus_points": [
      {
        "name": "九龙灌浴几点开始表演",
        "count": 6
      }
    ],
    "emotion_trend": [
      {
        "date": "2026-05-05",
        "positive": 1,
        "neutral": 8,
        "negative": 0
      }
    ],
    "service_suggestions": [
      "游客高频关注演出时间，建议在游客端首页固定展示九龙灌浴、吉祥颂等核心演出时刻。"
    ]
  }
}
```

## 11. 文档上传

- 地址：`POST /api/admin/docs/upload`
- 支持格式：`.txt`、`.md`、`.docx`、`.xlsx`

## 12. 知识库管理

### 11.1 文档列表

- 地址：`GET /api/admin/docs`
- 用途：查看已导入的知识文档、来源、状态、格式和知识片段数量

### 11.2 文档详情

- 地址：`GET /api/admin/docs/{document_id}`
- 用途：查看指定文档下的知识片段

### 11.3 修改文档信息

- 地址：`PATCH /api/admin/docs/{document_id}`
- 请求体：

```json
{
  "name": "灵山胜境讲解词.txt",
  "source": "admin",
  "status": "active"
}
```

### 11.4 删除文档

- 地址：`DELETE /api/admin/docs/{document_id}`
- 用途：删除文档及其对应的知识片段

### 11.5 重新导入文档

- 地址：`POST /api/admin/docs/{document_id}/reimport`
- 说明：仅当 `data/raw` 中仍存在同名原始文件时可用

### 11.6 新增知识片段

- 地址：`POST /api/admin/docs/{document_id}/chunks`
- 请求体：

```json
{
  "title": "九龙灌浴演出时间",
  "content": "九龙灌浴平日演出时间为10:00、11:30、13:30、15:00。",
  "tags": "演出,时间"
}
```

### 11.7 编辑知识片段

- 地址：`PATCH /api/admin/docs/chunks/{chunk_id}`

### 11.8 删除知识片段

- 地址：`DELETE /api/admin/docs/chunks/{chunk_id}`

## 13. 数字人配置

### 12.1 获取当前数字人配置

- 地址：`GET /api/digital-human/config`

### 12.2 保存数字人配置

- 地址：`POST /api/admin/digital-human/config`
- 请求体：

```json
{
  "name": "灵灵",
  "role_title": "景区 AI 导览员",
  "scenic_area": "灵山胜境",
  "outfit_theme": "ling-shan",
  "voice_name": "zh-CN-XiaoxiaoNeural",
  "greeting": "当前示范景区为灵山胜境，已接入对应知识库、路线推荐与语音播报能力。",
  "avatar_asset_url": "/app/assets/avatar/avatar-guide-v1.png",
  "video_provider_status": "外部视频 API",
  "fallback_message": "数字人视频暂不可用，已切换为语音讲解。",
  "service_boundary": "仅基于景区知识库进行导览讲解，不提供功德承诺、神迹保证或占卜预测。"
}
```

### 12.3 上传数字人形象素材

- 地址：`POST /api/admin/digital-human/avatar`
- 表单参数：`file`
- 支持格式：PNG、WebP、AVIF、GIF、JPG/JPEG；透明背景优先使用 PNG、WebP、AVIF 或 GIF
- 返回：更新后的数字人配置，`avatar_asset_url` 会指向已上传素材

### 12.4 数字人视频服务状态

- 地址：`GET /api/admin/digital-video/status`
- 用途：展示启用状态、最近状态、平均耗时、回退次数和最近失败原因

## 14. RAG 向量检索

后端配置项：

```dotenv
EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=https://api.edgefn.net/v1
EMBEDDING_MODEL=BAAI/bge-m3
ENABLE_RAG=true
RAG_TOP_K=5
```

说明：`EMBEDDING_API_KEY` 只写入本地 `.env`，不要写入代码、文档或 Git；Key 缺失或接口失败时，系统会自动回退到模板和关键词检索。

### 13.1 查看 RAG 状态

- 地址：`GET /api/admin/rag/status`
- 用途：查看 RAG 是否启用、Embedding 是否配置、已索引片段数、向量维度、最近构建时间和失败原因

### 13.2 重建向量索引

- 地址：`POST /api/admin/rag/rebuild`
- 请求体：

```json
{
  "document_name": null
}
```

- 说明：`document_name` 为空时重建全部有效知识片段；指定文档名时只重建该文档。

## 15. 核心 AI 状态与验收评测

### 15.1 核心 AI 能力状态

- 地址：`GET /api/admin/ai/status`
- 用途：查看中文主模型、RAG、中文 TTS、英文回答、口型同步和外部视频服务是否可用

### 15.2 读取最近一次验收评测

- 地址：`GET /api/admin/evaluation/latest`

### 15.3 运行验收评测

- 地址：`POST /api/admin/evaluation/run`
- 用途：自动运行标准问题集，返回准确率、平均耗时、P95 耗时和逐题命中情况
- 验收阈值：准确率不低于 90%，P95 响应耗时不超过 5.00 秒

返回体示例：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total_cases": 6,
    "passed_cases": 6,
    "accuracy_rate": 1.0,
    "average_latency_seconds": 1.42,
    "latency_p95_seconds": 2.31,
    "passed": true,
    "model_name": "GLM-5.1",
    "case_results": []
  }
}
```

## 16. 英文回答服务配置

后端配置项：

```dotenv
ENABLE_ENGLISH_TRANSLATION=true
ENGLISH_MODEL_API_KEY=
ENGLISH_MODEL_BASE_URL=https://api.openai-like.example/v1
ENGLISH_MODEL_NAME=gpt-4.1-mini
ENABLE_ENGLISH_TTS=true
ENGLISH_TTS_VOICE=en-US-JennyNeural
```

说明：

- `ENGLISH_MODEL_*` 只用于英文回答与英文语音，不影响中文主问答链路
- 真实英文模型密钥只写入本地 `.env`，不要写入代码、文档或 Git
- 修改 `.env` 后需要重启后端服务

## 17. 外部数字人视频服务协议

后端配置项：

```dotenv
DIGITAL_VIDEO_ENABLED=true
DIGITAL_VIDEO_BASE_URL=https://gpu.example.com
DIGITAL_VIDEO_API_KEY=replace-with-token
DIGITAL_VIDEO_AVATAR_ID=default
DIGITAL_VIDEO_TIMEOUT_SECONDS=8
```

后端请求：

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

