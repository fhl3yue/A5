# B端联调说明

## 1. 当前可直接接入的接口

以下接口已经完成，可直接供前端和管理端联调：

### 1.1 游客端接口

- `POST /api/chat/text`
- `POST /api/chat/voice`
- `POST /api/recommend/route`
- `POST /api/feedback`

### 1.2 管理端接口

- `POST /api/admin/login`
- `GET /api/admin/logs`
- `GET /api/admin/dashboard`
- `POST /api/admin/docs/upload`

## 2. 推荐前端接入顺序

建议 B 端按下面顺序接，不容易卡住：

1. 先接 `POST /api/chat/text`
2. 再接 `POST /api/recommend/route`
3. 再接 `POST /api/admin/login`
4. 再接 `GET /api/admin/dashboard`
5. 最后接 `POST /api/chat/voice`

这样即使语音页面还没完全好，文本问答和后台也能先跑通。

## 3. 游客端接入说明

## 3.1 文本问答

接口：

`POST /api/chat/text`

请求体：

```json
{
  "question": "九龙灌浴几点开始表演",
  "user_id": "U0001"
}
```

前端重点使用返回字段：

- `data.log_id`
- `data.transcript`
- `data.interpreted_question`
- `data.answer`
- `data.audio_url`
- `data.reference`
- `data.response_seconds`

页面建议展示：

- 用户输入问题
- 数字人回答文本
- 参考来源
- 播放按钮
- 满意度按钮

## 3.2 语音问答

接口：

`POST /api/chat/voice`

提交方式：

- `multipart/form-data`

字段说明：

- `transcript`：可选
- `user_id`：必填建议有
- `file`：音频文件，可选但正常语音场景需要传

推荐前端处理逻辑：

1. 用户录音后上传 `file`
2. 拿到返回结果后展示
3. 显示 `transcript` 作为“识别结果”
4. 显示 `interpreted_question` 作为“系统理解的问题”
5. 播放 `audio_url`

如果前端自己做浏览器端语音转写，也可以：

- 不传 `file`
- 直接传 `transcript`

## 3.3 路线推荐

接口：

`POST /api/recommend/route`

请求体：

```json
{
  "interest": "历史文化",
  "duration": "半天"
}
```

建议前端提供以下选项：

- 历史文化
- 佛教文化
- 自然风光
- 亲子休闲

时长建议：

- 半天
- 全天

前端重点展示字段：

- `route_name`
- `route_spots`
- `reason`

## 3.4 满意度反馈

接口：

`POST /api/feedback`

请求体：

```json
{
  "log_id": 11,
  "satisfaction": 5
}
```

说明：

- `log_id` 必须来自本次问答返回结果
- `satisfaction` 范围为 `1-5`

建议前端按钮：

- 非常满意：5
- 满意：4
- 一般：3
- 不满意：2
- 很差：1

## 4. 管理端接入说明

## 4.1 登录

接口：

`POST /api/admin/login`

请求体：

```json
{
  "username": "admin",
  "password": "admin123"
}
```

当前版本返回的是演示 token，可直接用于前端页面登录态展示。

## 4.2 数据看板

接口：

`GET /api/admin/dashboard`

重点字段：

- `today_visitors`
- `today_qa_count`
- `satisfaction_rate`
- `hot_questions`
- `emotion_distribution`

页面建议：

- 顶部 3 个统计卡片
- 热门问题柱状图
- 情绪分布饼图

## 4.3 问答日志

接口：

`GET /api/admin/logs?limit=50`

重点字段：

- `id`
- `user_id`
- `question`
- `answer`
- `emotion`
- `satisfaction`
- `response_seconds`
- `source_titles`
- `created_at`

页面建议：

- 表格形式展示
- 支持展开查看完整回答

## 4.4 知识文档上传

接口：

`POST /api/admin/docs/upload`

支持格式：

- `.txt`
- `.md`
- `.docx`
- `.xlsx`

说明：

- 上传后后端会自动导入知识片段
- 前端只需做文件选择和结果提示

## 5. 当前返回字段说明

## 5.1 文本和语音问答统一字段

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "log_id": 11,
    "transcript": "九龙灌浴几点开始表演",
    "interpreted_question": "九龙灌浴几点开始表演",
    "answer": "......",
    "audio_url": "/generated/audio/answer_xxx.mp3",
    "emotion": "neutral",
    "reference": [
      "九龙灌浴",
      "灵山胜境",
      "灵山大佛"
    ],
    "response_seconds": 1.315
  }
}
```

字段用途建议：

- `transcript`：显示原始识别结果
- `interpreted_question`：显示系统理解后的最终问题
- `answer`：主回答区
- `audio_url`：语音播放
- `reference`：参考来源标签
- `response_seconds`：可用于调试或开发态展示

## 6. 当前已知说明

### 6.1 可直接用于联调

- 文本问答已稳定
- 路线推荐已稳定
- 后台登录已稳定
- 数据看板已稳定
- 满意度反馈已稳定
- 语音问答已可用

### 6.2 语音效果说明

- 语音问答已支持真实音频上传
- 推荐演示时使用“人录的短问题音频”
- 不推荐拿系统生成的长回答音频再反向识别做展示

### 6.3 推荐的演示问题

- 九龙灌浴几点开始表演
- 灵山大佛有什么文化含义
- 我对历史文化感兴趣，推荐一条路线
- 我只有半天时间，怎么游览

## 7. 推荐页面展示方案

## 7.1 游客端

- 聊天窗口
- 数字人头像区
- 文本输入框
- 录音按钮
- 识别结果展示
- 系统理解结果展示
- 回答语音播放按钮
- 满意度按钮

## 7.2 管理端

- 登录页
- 数据看板页
- 问答日志页
- 知识库上传页

## 8. 演示前建议

每次演示前建议先执行：

```powershell
powershell -ExecutionPolicy Bypass -File D:\software\reset_demo_env.ps1
```

如果要彻底恢复到干净数据状态：

```powershell
powershell -ExecutionPolicy Bypass -File D:\software\reset_demo_env.ps1 -Full
```

## 9. 服务地址

- 后端服务：`http://127.0.0.1:8000`
- Swagger：`http://127.0.0.1:8000/docs`

## 10. 当前结论

当前 A 端已经达到可交给 B 端并行接入的状态，B 端不需要等待 A 端再补核心接口，可以直接开始游客端和后台管理页面联调。
