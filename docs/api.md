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
- 文本问答与语音问答在成功时都会尽量返回 `audio_url`，前端可直接播放该地址

## 4. 路线推荐

- 地址：`POST /api/recommend/route`
- 请求体：

```json
{
  "interest": "历史文化",
  "duration": "半天"
}
```

## 5. 满意度反馈

- 地址：`POST /api/feedback`
- 请求体：

```json
{
  "log_id": 1,
  "satisfaction": 5
}
```

## 6. 管理员登录

- 地址：`POST /api/admin/login`

## 7. 问答日志

- 地址：`GET /api/admin/logs?limit=50`

## 8. 数据看板

- 地址：`GET /api/admin/dashboard`
- 用途：展示当日服务数据、热门问题、情绪分布、本周服务趋势和满意度趋势

## 9. 游客感受度报告

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

## 10. 文档上传

- 地址：`POST /api/admin/docs/upload`
- 支持格式：`.txt`、`.md`、`.docx`、`.xlsx`

## 11. 知识库管理

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

## 12. 数字人配置

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
  "greeting": "当前示范景区为灵山胜境，已接入对应知识库、路线推荐与语音播报能力。"
}
```
