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

## 9. 文档上传

- 地址：`POST /api/admin/docs/upload`
- 支持格式：`.txt`、`.md`、`.docx`、`.xlsx`
