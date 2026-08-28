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

视觉模型尚未绑定具体权重。当前分析器会生成可替换的候选事件，下一步将把球员检测、跟踪、号码 OCR 和事件识别接入 `run_analysis`，不改变前端 API 契约。

## 接入视觉模型

将训练好的 YOLO 权重放到 `models/basketball-yolo.pt`，并安装可选依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install ultralytics torch torchvision
```

也可以通过环境变量指定权重：

```powershell
$env:COURTTRACE_MODEL = 'D:\models\basketball-yolo.pt'
```

当前适配器已经完成视频抽帧和检测调用。球员跟踪、号码 OCR、球队颜色聚类和投篮命中判断需要使用针对篮球场景标注的数据训练专用权重，不能直接用通用 COCO 权重代替。
