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
