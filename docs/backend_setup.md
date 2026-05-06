# A端启动说明

## 1. 安装依赖

```powershell
cd D:\software
python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt
Copy-Item .env.example .env
```

## 2. 初始化数据库

```powershell
$env:PYTHONPATH='D:\software\backend'
python scripts\init_db.py
python scripts\import_sample_data.py
python scripts\import_official_materials.py
```

## 3. 启动服务

```powershell
$env:PYTHONPATH='D:\software\backend'
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir D:\software\backend
```

或者直接执行：

```powershell
powershell -ExecutionPolicy Bypass -File D:\software\start_backend.ps1
```

启动成功后可以访问：

- 前端演示页面：`http://127.0.0.1:8000/app/`
- 接口文档页面：`http://127.0.0.1:8000/docs`

当前前端页面由后端直接托管，因此不需要单独启动 Vue、React 或 Vite 服务。

首次使用语音识别时，`faster-whisper` 会自动下载对应模型，默认配置为 CPU 上的 `base` 模型，首次加载会稍慢，后续会复用缓存。

如果你们后期觉得识别不够准，可优先尝试两种方式：

1. 把 `.env` 里的 `ASR_MODEL_SIZE` 从 `tiny` 调整为 `base` 或 `small`
2. 调整 `ASR_INITIAL_PROMPT`，加入更多景区专有名词

## 4. 默认账号

- 用户名：`admin`
- 密码：`admin123`

## 5. 重置演示环境

只清空问答日志和生成音频：

```powershell
powershell -ExecutionPolicy Bypass -File D:\software\reset_demo_env.ps1
```

完整重置数据库并重新导入样例和官方资料：

```powershell
powershell -ExecutionPolicy Bypass -File D:\software\reset_demo_env.ps1 -Full
```
