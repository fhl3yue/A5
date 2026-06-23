# 景区导览 AI 数字人项目复刻说明

本仓库是“景区导览服务 AI 数字人”项目的本地演示版，包含游客端 H5 页面、管理端、FastAPI 后端、本地景区知识库、RAG 检索、中文/英文回答、多模态图片识别和数字人口型同步演示能力。

当前推荐分支：

```powershell
codex/saas-dark-glass-ui
```

## 1. 队友电脑准备

队友电脑需要先安装：

- Git
- Python 3.11 或 3.12
- Windows PowerShell
- 可访问模型中转服务的网络环境

Node.js 不是启动项目必须项，只用于前端语法检查。

## 2. 克隆项目

建议直接克隆到 `D:\software`，这样和当前开发机路径一致，少踩路径坑。

```powershell
git clone -b codex/saas-dark-glass-ui https://github.com/fhl3yue/A5.git D:\software
cd D:\software
```

如果队友已经克隆过项目，可以进入项目目录后执行：

```powershell
git fetch origin
git checkout codex/saas-dark-glass-ui
git pull
```

## 3. 安装 Python 依赖

```powershell
cd D:\software
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\pip install -r backend\requirements.txt
```

如果安装 `faster-whisper` 较慢，可以先等待完成；它主要用于语音识别能力。

## 4. 配置 `.env`

`.env` 不会上传到 GitHub，因为里面包含模型 Key。队友复刻时有两种方式。

方式一：直接复制你的 `.env`

把你本机的：

```text
D:\software\.env
```

复制到队友项目根目录：

```text
D:\software\.env
```

方式二：从模板创建

```powershell
Copy-Item .env.example .env
notepad .env
```

至少需要填写这些字段：

```env
MODEL_API_KEY=你的中转Key
ENGLISH_MODEL_API_KEY=你的中转Key
EMBEDDING_API_KEY=你的中转Key
VISION_MODEL_API_KEY=你的中转Key
```

当前主要模型配置建议保持：

```env
MODEL_BASE_URL=https://api.edgefn.net/v1
MODEL_NAME=GLM-5.1
EMBEDDING_BASE_URL=https://api.edgefn.net/v1
EMBEDDING_MODEL=BAAI/bge-m3
VISION_MODEL_BASE_URL=https://api.edgefn.net/v1
VISION_MODEL_NAME=GLM-4.5V
```

注意：如果队友电脑路径不是 `D:\software`，也可以运行，但 `.env` 中的本地材料目录可能需要调整。

## 5. 启动后端和页面

```powershell
cd D:\software
powershell -ExecutionPolicy Bypass -File .\start_backend.ps1
```

启动成功后打开：

```text
游客端/管理端页面：http://127.0.0.1:8000/app/
API 文档：http://127.0.0.1:8000/docs
```

管理端默认账号：

```text
admin / admin123
```

不要直接在浏览器打开下面这种地址：

```text
http://127.0.0.1:8000/api/admin/rag/rebuild
```

这是 POST 接口，不是网页入口。直接打开会失败或无意义。

## 6. 初始化与重建 RAG

项目首次启动时会自动创建 SQLite 数据库，并导入 `data\sample` 中的基础景区数据。

如果已经填写 `EMBEDDING_API_KEY`，建议启动后重建一次 RAG 向量索引。

方式一：在管理端点击“重建向量索引”按钮。

方式二：使用 PowerShell POST 请求：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/admin/rag/rebuild" -Method POST
```

查看 RAG 状态：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/admin/rag/status" -Method GET
```

## 7. 验证复刻是否成功

查看 AI 能力状态：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/admin/ai/status" -Method GET
```

运行 50 题自测：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/admin/evaluation/run" -Method POST
```

文本问答烟测：

```powershell
$body = @{
  question = "九龙灌浴几点开始表演"
  user_id = "teammate-check"
  tts_mode = "local_preferred"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/chat/text" -Method POST -ContentType "application/json" -Body $body
```

如果返回中包含 `10:00`、`11:30` 等演出时间，说明本地知识库和问答链路基本正常。

## 8. 官方材料可选复刻

基础演示只需要仓库内置 `data\sample` 数据。

如果要尽量复刻当前开发机的完整知识库，可以额外把官方材料目录发给队友，例如：

```text
C:\Users\LWQ\Documents\Playground\cnsoftbei_a5_data
```

队友收到后，在 `.env` 中修改：

```env
OFFICIAL_MATERIALS_DIR=队友电脑上的材料目录
```

然后运行：

```powershell
$env:PYTHONPATH="D:\software\backend"
$env:SCENIC_AI_BASE_DIR="D:\software"
.\.venv\Scripts\python scripts\import_official_materials.py
```

导入后再次重建 RAG 向量索引。

## 9. 常见问题

### 9.1 浏览器显示 127.0.0.1 拒绝连接

说明后端没有启动。重新运行：

```powershell
cd D:\software
powershell -ExecutionPolicy Bypass -File .\start_backend.ps1
```

### 9.2 打开 `/api/admin/rag/rebuild` 没反应或报错

这是正常的。该接口必须用 POST 请求调用，不能当网页直接打开。

正确入口是：

```text
http://127.0.0.1:8000/app/
```

### 9.3 RAG 显示未配置或索引数量为 0

检查 `.env` 是否填写：

```env
EMBEDDING_API_KEY=
```

填写后重启后端，并重建向量索引。

### 9.4 图片识别不可用

检查 `.env` 是否填写：

```env
VISION_MODEL_API_KEY=
VISION_MODEL_NAME=GLM-4.5V
VISION_MODEL_BASE_URL=https://api.edgefn.net/v1
```

如果中转服务临时不可用，文本问答和 RAG 不受影响。

### 9.5 语音音色和你的电脑不一样

游客端桌面浏览器默认优先使用浏览器本地朗读，音色由队友电脑和浏览器决定，不一定等同于服务端 `TTS_VOICE=zh-CN-XiaoxiaoNeural`。

如果想尽量统一音色，可以改用服务端音频生成，但首次生成会更慢。

## 10. 提交前检查命令

如果队友修改代码，提交前建议运行：

```powershell
cd D:\software\backend
D:\software\.venv\Scripts\python.exe -m unittest discover -s tests
```

后端编译检查：

```powershell
cd D:\software
D:\software\.venv\Scripts\python.exe -m compileall D:\software\backend\app
```

前端语法检查：

```powershell
node --check D:\software\frontend\app.js
```

Git 空白检查：

```powershell
git diff --check
```

## 11. 最小复刻结论

普通复刻只需要：

```text
代码 + Python 依赖 + .env
```

完整复刻建议再加：

```text
官方材料目录 + RAG 重建 + 50 题评测
```
## LiteAvatar 真人数字人视频层（当前推荐）

当前推荐方案不是把完整 OpenAvatarChat 网页嵌进 A5，而是只抽离 LiteAvatar 人物渲染核心作为 `avatar-only sidecar`。它只接收 A5 已生成的语音文件，输出带真人数字人和口型的 MP4；不启动摄像头、ASR、RTC 聊天 UI，也不接管 A5 的 RAG/问答链路。

OpenAvatarChat 实验项目建议单独放在：

```text
D:\OpenAvatarChatLab\OpenAvatarChat
```

启动 avatar-only sidecar：

```powershell
powershell -ExecutionPolicy Bypass -File D:\OpenAvatarChatLab\OpenAvatarChat\run_a5_liteavatar_avatar_only.ps1 -Preload
```

在 `D:\software\.env` 中启用 A5 接入：

```env
AVATAR_ONLY_ENABLED=true
AVATAR_ONLY_BASE_URL=http://127.0.0.1:18085
AVATAR_ONLY_TIMEOUT_SECONDS=45
OPENAVATAR_ENABLED=false
```

然后启动 A5 后端：

```powershell
cd D:\software
powershell -ExecutionPolicy Bypass -File .\start_backend.ps1
```

工作链路：

```text
A5 问答/RAG -> A5 生成中文语音 -> avatar-only sidecar 生成 MP4 -> 游客端出现“数字人讲解”按钮
```

性能注意：

- CPU 模式首次冷启动会加载模型，1.5 秒测试音频实测约 33 秒。
- 预热后可减少首次等待；相同音频再次请求会命中缓存，实测 `cached=true` 且接近即时。
- 如果 sidecar 未启动或生成失败，A5 会继续保留文字、语音和普通口型兜底，不影响问答、RAG、语音和后台。

完整 OpenAvatarChat 的 `8282` iframe 实验层仍保留为历史备用方案，但不建议作为默认演示路线。

## A5 与 LiteAvatar 一键联动启动

当前推荐演示方式是只启动 `avatar-only sidecar`，不启动完整 OpenAvatarChat UI。`start_backend.ps1` 已经和 LiteAvatar 建立联动：

```powershell
cd D:\software
powershell -ExecutionPolicy Bypass -File .\start_backend.ps1
```

如果 `D:\software\.env` 中存在：

```env
AVATAR_ONLY_ENABLED=true
AVATAR_ONLY_BASE_URL=http://127.0.0.1:18085
OPENAVATAR_ROOT=D:\OpenAvatarChatLab\OpenAvatarChat
```

启动 A5 后端前，脚本会先检查 `http://127.0.0.1:18085/health`。如果 LiteAvatar sidecar 没有运行，会自动执行：

```powershell
powershell -ExecutionPolicy Bypass -File D:\OpenAvatarChatLab\OpenAvatarChat\run_a5_liteavatar_avatar_only.ps1 -Preload
```

如果临时只想启动 A5 后端、不启动真人数字人 sidecar，可以使用：

```powershell
powershell -ExecutionPolicy Bypass -File .\start_backend.ps1 -SkipAvatarOnly
```
