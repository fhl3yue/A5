# Claude 数字人形象交接说明

本文档用于把“数字人形象相关工作”交接给 Claude 或其他视觉/前端协作者。请先完整阅读再动代码，避免重复踩坑。

## 1. 项目背景

项目是“景区导览 AI 数字人”系统，当前示范景区为“灵山胜境”。整体系统已经具备：

- 游客端 H5 页面：`/app/`
- 管理端后台：同一页面内切换
- 本地景区知识库与 RAG 问答
- 文本/语音问答
- 英文翻译
- 图片识别导览
- 路线推荐
- 语音播报
- 数字人口型/表情联动
- 后台状态与评测面板

数字人形象不是独立小玩具，它要服务赛题要求：

> 数字人能以语音、表情和口型同步的方式进行回答。

所以最终目标不是单纯“好看头像”，而是“游客端可接受的角色形象 + 可解释的口型同步与表情驱动”。

## 2. 当前视觉状态

当前游客端默认形象已经回退为较稳定的导览员立绘：

```text
frontend/assets/avatar/avatar-guide-v1.png
```

当前本机配置也已切回：

```text
outfit_theme = asset-avatar
avatar_asset_url = /app/assets/avatar/avatar-guide-v1.png
```

这张立绘虽然不是完美方案，但至少不会吓人，适合先保住演示效果。

请注意：之前我们尝试把 `bio-face-rig` 直接作为游客端默认形象，结果视觉效果非常粗糙，用户反馈“像吓人脸”。因此现在的结论是：

- `bio-face-rig` 可以保留为技术原型或后台调试证明。
- `bio-face-rig` 当前版本不能直接作为游客端正式形象。
- 后续如果要启用 Rig，必须先重做视觉稿，而不是把现有原型脸放上去。

## 3. 已实现的数字人技术链路

### 3.1 前端形象层

相关文件：

```text
frontend/index.html
frontend/styles.css
frontend/app.js
frontend/assets/avatar/avatar-guide-v1.png
```

`frontend/index.html` 里目前同时存在：

- 稳定 PNG 立绘层：`.licensed-avatar-layer`
- 工程原型 SVG 面部 Rig：`.bio-face-rig`
- 旧 Live2D 风格 SVG：`.pet-character / .live2d-character`
- 外部视频层：`.digital-video-layer`

当前游客端默认应该显示 PNG 立绘层，不应该显示粗糙的 `bio-face-rig`。

### 3.2 表情与口型驱动

`frontend/app.js` 已有统一驱动入口：

```js
applyFaceRig(params)
```

它通过 CSS 变量控制：

- `mouthOpen`
- `mouthShape`
- `eyeOpen`
- `browLift`
- `headYaw`
- `headPitch`
- `smile`

当前即使显示 PNG 立绘，也保留了音频播放时的舞台光效、轻微缩放、状态动画。若未来换成高质量 SVG/Live2D 风格形象，可以直接复用这些参数。

### 3.3 口型同步来源

当前有三层：

1. 浏览器本地朗读节奏模拟
   - 用 `speechSynthesis` 尽快让游客听到语音。
   - 没有 MP3 文件时，用节奏和边界事件模拟嘴型。

2. Web Audio RMS 兜底
   - 播放音频时分析实时振幅。
   - 用音量大小驱动嘴巴开合、头部和光效。

3. Rhubarb Lip Sync 可选增强
   - 服务端已新增 `backend/app/services/lipsync.py`。
   - `/api/chat/audio/{log_id}` 可返回 `lipsync_url`、`lipsync_provider`、`mouth_cue_count`。
   - 默认关闭：`ENABLE_RHUBARB_LIPSYNC=false`。
   - 如果安装 `tools/rhubarb/rhubarb.exe` 并开启配置，可生成更准确的 mouth cues。

相关文件：

```text
backend/app/services/lipsync.py
backend/app/services/audio_tasks.py
backend/app/schemas.py
backend/app/main.py
scripts/check_rhubarb_lipsync.ps1
docs/2D仿生面部关键点数字人说明.md
```

## 4. 之前踩过的坑

### 坑 1：工程原型不等于游客端成品

`bio-face-rig` 的初衷是证明“面部关键点、嘴型、眉眼可以被参数驱动”，但它不是成熟美术。直接切到游客端会显得廉价甚至吓人。

如果 Claude 接手，请不要简单地把现有 `bio-face-rig` 放大、美颜后继续当正式形象。应重新设计角色视觉。

### 坑 2：不要为了口型同步牺牲首屏观感

赛题要求口型同步，但评委第一眼看到的是角色形象和页面完整度。如果角色不好看，技术点反而会扣印象分。

建议优先级：

```text
游客第一眼不出戏 > 角色与景区气质匹配 > 能看出口型/表情动 > 技术说明足够可信
```

### 坑 3：不要引入重依赖导致项目跑不起来

当前项目是 FastAPI + 静态 H5，重点是稳定演示。不要轻易强行接入需要复杂安装的：

- 3D 引擎
- 大型视频生成模型
- GPU 推理
- Conda 重环境
- 未授权 Live2D 模型
- 侵权虚拟偶像素材

如果要引入新方案，必须保证：

- Windows 本机能跑。
- 不影响 `/api/chat/text`、`/api/chat/voice`、`/app/` 主流程。
- 失败时能回退到 PNG 立绘。

## 5. Claude 接手建议路线

### 第一优先级：做一个真正能看的游客端形象

建议不要直接改业务逻辑，先只改视觉层：

- 保留 `avatar-guide-v1.png` 作为兜底。
- 新增一套更精致的 2D 角色层，比如：
  - SVG 分层角色
  - CSS/Canvas 分层角色
  - 自制透明 PNG 序列
  - 合法授权 Live2D/Spine 资产的 Web 展示层

视觉方向建议：

- 景区导览员，不要二次元过头。
- 干净、亲和、可信。
- 服装可以结合青绿、白色、金色胸牌。
- 面部不要过度写实，避免恐怖谷。
- 移动端 390px 宽度下仍然清楚。

### 第二优先级：让嘴型动得自然一点

如果用 SVG 分层角色，建议至少拆出：

- 头部整体
- 左眼/右眼
- 左眉/右眉
- 嘴巴闭口
- 嘴巴微开
- 嘴巴大开
- 圆唇
- 微笑

然后接入现有 CSS 变量：

```css
--mouth-open
--face-mouth-x
--face-mouth-a
--face-mouth-o
--face-mouth-e
--face-mouth-f
--face-eye-open
--face-brow-lift
--face-head-yaw
--face-head-pitch
--face-smile
```

前端 JS 已经会写这些变量，不建议重写问答和语音逻辑。

### 第三优先级：增加“调试/答辩证明层”

可以做一个只在管理端或 `?debugFace=1` 时显示的调试面板，展示：

- 当前口型：A/O/E/X 等
- 当前音量振幅
- 当前表情参数
- 是否使用 Rhubarb
- mouth cue 数量

游客端不要显示这些工程信息。

## 6. 文件修改边界

Claude 优先修改：

```text
frontend/index.html
frontend/styles.css
frontend/app.js
frontend/assets/avatar/
docs/2D仿生面部关键点数字人说明.md
```

尽量不要修改：

```text
backend/app/services/chat.py
backend/app/services/rag.py
backend/app/services/vision.py
backend/app/services/audio.py
```

除非确实要调整口型同步接口，否则不要动后端问答、RAG、图片识别、英文翻译和 TTS 主流程。

运行时产物不要提交：

```text
.env
data/generated/
.venv/
.venv_tts/
local_tts/
tools/rhubarb/
```

## 7. 当前 Git 状态提醒

当前工作区有不少未提交改动，包括：

- Edge TTS 缓存
- MOSS 试验文档
- Rhubarb lipsync 服务
- 2D 仿生 Rig 原型
- H5 视觉调整
- 多模态图片识别修复

Claude 接手前最好先看：

```powershell
git status --short --branch
git diff -- frontend/index.html frontend/styles.css frontend/app.js
```

不要随手 revert 用户已有改动，也不要把 `.env` 或生成文件加入 Git。

## 8. 验收标准

Claude 改完后，至少要满足：

- 游客端第一眼不突兀、不吓人。
- 手机端 390x844 无横向溢出。
- 数字人不能遮挡标题、输入框、问答区。
- 点击“语音播放”时能看到嘴部或表情有明显联动。
- 文本问答、语音播放、英文翻译、图片上传不被破坏。
- 管理端仍能切换或上传形象。

检查命令：

```powershell
node --check D:\software\frontend\app.js
D:\software\.venv\Scripts\python.exe -m compileall D:\software\backend\app
git diff --check
```

如果改了后端，再补跑：

```powershell
cd D:\software\backend
D:\software\.venv\Scripts\python.exe -m unittest discover -s tests
```

## 9. 给 Claude 的一句话任务

请在不破坏现有问答/RAG/TTS/图片识别功能的前提下，重做游客端数字人视觉层。当前默认 PNG 立绘可保留为兜底；现有 `bio-face-rig` 只是工程原型，不能直接作为正式游客形象。目标是做出一个“美观、亲和、能口型/表情联动、适合景区导览场景”的 2D 数字人，并让它能复用现有 `applyFaceRig()` 参数驱动链路。
