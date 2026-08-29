# COURTTRACE

本地篮球比赛视频统计工作台。当前版本包含 Vue 前端和 FastAPI 本地服务：视频保存在 `data/uploads`，元数据保存在 `data/courttrace.sqlite3`。

## 启动

前端：

```powershell
npm install
npm run dev
```

后端：

```powershell
.\start-backend.ps1
```

打开 `http://127.0.0.1:5173/`。

## 换电脑使用

新电脑需要先安装以下环境：

- Git
- Git LFS
- Node.js 18 或更高版本
- Python 3.11 或更高版本
- PowerShell
- FFmpeg（视频抽帧和时长读取需要）

从 Gitee 下载项目：

```powershell
git clone https://gitee.com/Cc7130194/basketball-video-stats.git
cd basketball-video-stats
git lfs pull
```

安装前端依赖：

```powershell
npm install
```

启动本地后端服务：

```powershell
.\start-backend.ps1
```

第一次运行后端时，脚本会自动创建 `.venv` 虚拟环境并安装 Python 依赖。后端默认运行在 `http://127.0.0.1:8000`。

保持后端终端运行，再打开一个新的 PowerShell 窗口，进入项目目录并启动前端：

```powershell
cd basketball-video-stats
npm run dev
```

浏览器打开：

```text
http://127.0.0.1:5173/
```

如果项目目录不在当前终端所在位置，请将 `cd basketball-video-stats` 替换为实际项目路径，例如：

```powershell
cd D:\projects\basketball-video-stats
```

停止服务时，分别在前端和后端终端按 `Ctrl + C`。

后端启动脚本会创建 `.venv` 并安装 `backend/requirements.txt`。服务默认运行在 `http://127.0.0.1:8000`。

## 已接入接口

- `GET /api/health`：检测 CUDA、PyTorch、FFmpeg 和 FFprobe
- `POST /api/matches/{match_id}/clips`：批量上传视频，按 SHA-256 去重
- `GET /api/matches/{match_id}/clips`：读取本地片段记录
- `POST /api/matches/{match_id}/analyze`：创建本地分析任务
- `GET /api/tasks/{task_id}`：轮询分析进度
- `GET /api/matches/{match_id}/events`：读取候选事件

视觉分析已接入球员、篮球和球场关键点三份预训练权重。当前会生成疑似投篮和命中候选，所有候选仍需人工复核；球员跨片段跟踪、号码 OCR 和球队颜色聚类是后续识别阶段。

## 接入视觉模型

当前分析器使用三个独立权重：

- `models/player_detector.pt`：球员、篮筐和裁判检测
- `models/ball_detector_model.pt`：篮球检测和轨迹采样
- `models/court_keypoint_detector.pt`：球场关键点检测

仓库通过 Git LFS 保存权重。克隆后先执行 `git lfs pull`；权重缺失时也可以运行：

```powershell
.\scripts\download-models.ps1
```

安装可选视觉依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install ultralytics torch torchvision
```

本项目也提供了 GTX 10 系列可用的 CUDA 11.8 依赖清单：

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-gpu.txt
```

没有 NVIDIA 显卡时只安装默认的 `backend/requirements.txt` 即可；有 NVIDIA 显卡时使用 `requirements-gpu.txt`，安装包约 3 GB。

也可以通过环境变量分别指定权重：

```powershell
$env:COURTTRACE_PLAYER_MODEL = 'D:\models\player_detector.pt'
$env:COURTTRACE_BALL_MODEL = 'D:\models\ball_detector_model.pt'
$env:COURTTRACE_COURT_MODEL = 'D:\models\court_keypoint_detector.pt'
```

当前适配器已经完成视频抽帧、多模型 GPU 推理、球员/篮球/篮筐类别提取、球场关键点统计和疑似投篮轨迹判断。球员跨片段身份、号码 OCR 和球队颜色聚类仍需继续接入；所有 AI 事件默认进入人工复核，不直接作为最终统计。
