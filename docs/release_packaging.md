# 发行版打包说明

## 1. 目标

本说明用于把当前项目整理成 Windows 演示包，交付形态为 `dist\scenic-ai-guide-demo` 目录。目录内包含可执行启动器、前端静态文件、样例数据、运行配置和启动脚本。

## 2. 当前推荐形态

优先使用 Windows `.exe` 演示包：

- `scenic-ai-guide-demo.exe`：后端与前端托管启动器。
- `start_demo.ps1`：设置运行目录并启动 exe。
- `frontend`：游客端与管理端静态页面。
- `data\sample`：灵山胜境示范景区样例数据。
- `data\generated`：首次启动后自动生成，保存 SQLite 数据库、上传文件和问答音频。

APK 不建议作为当前第一版发行形态；若后续需要移动端安装包，建议采用 Android WebView + 云端 FastAPI API。

## 3. 打包命令

在 Windows PowerShell 中运行：

```powershell
powershell -ExecutionPolicy Bypass -File D:\software\scripts\build_windows_demo.ps1
```

脚本会使用 `.venv` 安装运行依赖和 PyInstaller，并输出：

```text
D:\software\dist\scenic-ai-guide-demo
```

## 4. 演示包启动

```powershell
powershell -ExecutionPolicy Bypass -File D:\software\dist\scenic-ai-guide-demo\start_demo.ps1
```

启动后访问：

- 前端页面：`http://127.0.0.1:8000/app/`
- 接口文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/api/health`

首次启动会自动创建数据库、管理员账号和样例数据。默认账号为 `admin / admin123`。

## 5. 发布前检查

发布演示包前检查 3 项：

1. `GET /api/health` 返回 `status: ok`。
2. 游客端可完成文本问答、路线推荐和满意度反馈。
3. 管理端可登录并加载看板、日志、知识库和数字人配置。

需要干净演示数据时，在源码目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File D:\software\reset_demo_env.ps1
```

## 6. GitHub 提交流程

当前成果分支为 `codex/scenic-ai-demo`，本地 `main` 不应强推到远程 `main`。

提交当前成果：

```powershell
git status --short
git add .gitignore backend\app\config.py backend\app\launcher.py backend\app\main.py scripts\build_windows_demo.ps1 docs\release_packaging.md README.md
git commit -m "build: add windows demo packaging guide"
git push origin main:codex/scenic-ai-demo
```

随后在 GitHub 仓库 `https://github.com/fhl3yue/A5` 中，从 `codex/scenic-ai-demo` 发起 Pull Request 合并到 `main`。
