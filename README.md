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

## 手机上传

桌面版启动后，电脑总览顶部会显示一个手机上传地址。手机和电脑连接同一个 Wi-Fi 后，用手机浏览器打开该地址即可选择比赛并批量上传视频；上传完成后电脑会自动创建增量分析任务。手机上传链接带有随机令牌，仅在当前桌面应用运行期间有效。

## 版本发布

版本号和自动更新约定见 [`docs/VERSIONING.md`](docs/VERSIONING.md)。普通应用发布使用 `npm version patch`、`npm version minor` 或 `npm version major`，再推送 tag；GitHub Actions 会自动生成 Windows 应用安装包和更新元数据。

## Windows 离线安装包

不希望在首次启动时从 GitHub 下载 Runtime 时，可以在项目目录中生成应用安装包和 Runtime 安装包：

```powershell
cd E:\basketball-video-stats
npm install
npm run desktop:runtime-installer
npm run desktop:package
```

构建完成后，`release` 目录中会生成：

```text
COURTTRACE-Runtime-Setup-0.1.1.exe
COURTTRACE-Setup-当前版本.exe
```

离线电脑必须按以下顺序安装：

1. 安装 `COURTTRACE-Runtime-Setup-0.1.1.exe`。
2. 安装 `COURTTRACE-Setup-当前版本.exe`。
3. 从桌面或开始菜单启动 COURTTRACE。

Runtime 安装包包含 Python 后端、PyTorch、Ultralytics、FFmpeg 和三个模型文件，体积较大，但安装后普通应用升级不需要再次安装 Runtime。

如果当前电脑已经具备可用的项目环境：

```text
Python 3.11 或 3.12
项目 .venv 和后端源码
PyTorch、Ultralytics、OpenCV
FFmpeg
三个模型文件
```

则只需要生成小型应用安装包：

```powershell
npm run desktop:package
```

桌面端会严格验证现有环境，验证通过后直接复用；环境不完整时才会回退到标准 Runtime 下载流程。

构建 Runtime 前需要确认本机已经安装 Inno Setup，并且 `.venv`、`models` 和 FFmpeg 均可用。构建产物位于 `release`，该目录不会提交到 Git。

也可以生成分卷离线分发目录：

```powershell
npm run desktop:offline
```

生成的 `release\COURTTRACE-Offline-版本号` 目录包含应用安装包、两个 Runtime 分卷、SHA-256 manifest、7za 和 `install-offline.ps1`。将整个目录复制到目标电脑后，右键使用 PowerShell 运行 `install-offline.ps1`；脚本会校验分卷、离线解压 Runtime、配置手机上传防火墙规则并安装应用，不访问 GitHub。所有文件必须保持在同一目录。

## 换电脑使用

新电脑需要先安装以下环境：

- Git
- Git LFS
- Node.js 18 或更高版本
- Python 3.11 或更高版本
- PowerShell
- FFmpeg（视频抽帧和时长读取需要）

从 GitHub 下载项目：

```powershell
git clone https://github.com/Wscthhh/basketball-video-stats.git
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

### 测试比赛数据

需要体验完整的球员、统计、复核和集锦界面时，可在已有 `integration-test` 视频的电脑上执行：

```powershell
.\.venv\Scripts\python.exe .\scripts\seed-test-match.py
```

该脚本只向 SQLite 写入明确标记为“测试”的比赛数据，不会在前端代码中注入演示常量，也不会影响正式比赛。

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

## FIBA 投篮类型判断

分析器使用现有球场模型的 18 个 FIBA 关键点，通过 RANSAC 单应性将出手球员脚点映射到 28×15 米标准球场：

- 罚球：出手点位于罚球线附近，并通过短时相对运动检查
- 两分：位于 6.75 米三分线内
- 三分：位于三分弧线或底角直线外
- 待判断：关键点不足、映射置信度不足，或脚点距离三分线小于 0.25 米

自动结果保存 `shotTypeConfidence`、球场坐标和单应性置信度。人工修正的分类不会被重新分析覆盖。

球员统计按已确认事件展示罚球、两分、三分的命中/出手以及总得分。

## 号码 OCR 与自动确认

号码识别使用 PaddleOCR 对稳定球员轨迹的上半身区域进行多帧投票，不对整张比赛画面做 OCR。只有同一号码满足多帧一致和置信度阈值时，才会绑定到临时球员；否则继续保留临时编号。

OCR 是可选依赖，安装方式：

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-ocr.txt
```

当前启用的自动确认策略仅针对高置信度命中：必须同时满足球员、球队、篮筐穿越、投篮类型和置信度条件。自动确认事件会记录 `confirmedBy=ai` 和 `confirmationRule`；投篮候选、低置信度命中和类型不明确的事件继续进入人工复核。

## 进球训练样本积累

当前可先不绑定球员，直接把复核队列中的事件确认成“命中”。系统会自动从原视频提取事件前后关键帧，写入：

```text
data/training/review/{matchId}/{sampleId}/frame-*.jpg
```

样本标签固定为 `make`，同时保存片段、事件时间、投篮类型和球员/球队归属（可为空）。查询当前比赛积累的样本：

```text
GET /api/matches/{match_id}/review-samples
```

后续可以基于这些未归属进球样本训练命中/未中模型，再单独做球员匹配，不会改变当前人工复核结果。

### 算法参考

- [abdullahtarek/basketball_analysis](https://github.com/abdullahtarek/basketball_analysis)：18 点 FIBA 球场映射、球员脚点和单应性思路；仓库未提供独立许可证文件，避免直接复制代码。
- [josephattalla/Basketball-Shot-Detection](https://github.com/josephattalla/Basketball-Shot-Detection)：MIT License，多篮球/篮筐跟踪和篮筐穿越判断。
- [DeepSportradar/camera-calibration-challenge](https://github.com/DeepSportradar/camera-calibration-challenge)：FIBA 摄像机标定数据和球场线分割基线，数据使用遵循挑战与数据集条款。
- [metacore-stack/RimPlane](https://github.com/metacore-stack/RimPlane)：球场区域和三分线几何参考；许可证禁止商业衍生使用，本项目只参考公开几何思想，不复制其实现。

## 社区项目参考

以下项目经过检索后作为实现参考，不作为当前项目的运行时依赖：

- [lin-simon/NBAction](https://github.com/lin-simon/NBAction)：Apache-2.0，提供篮球动作分类、投篮/得分检测思路，并包含 `best.pt` 和测试视频。
- [josephattalla/Basketball-Shot-Detection](https://github.com/josephattalla/Basketball-Shot-Detection)：MIT，提供篮球/篮筐轨迹、篮筐穿越和命中/未中判断。
- [sketscripter/Computer-vision-basketball-court-mapping-and-player-tracking](https://github.com/sketscripter/Computer-vision-basketball-court-mapping-and-player-tracking)：Apache-2.0，提供球员球队分类与球场映射参考。
- [Purgty/Basketball-Homography](https://github.com/Purgty/Basketball-Homography)：MIT，提供单应性、时序平滑和球员位置映射参考。
- [rustyneuron01/Real-Time-Football-Detection](https://github.com/rustyneuron01/Real-Time-Football-Detection)：MIT，虽然是足球项目，但其 ReID、ByteTrack、球队分类和相机运动处理思路适用于篮球视频。

检索时没有找到一个能直接覆盖“手机云台全场跟拍、球队归属、球员身份、投篮类型和完整技术统计”的成熟开源项目。因此当前实现采用多模型、轨迹、球队颜色和人工复核组合，不把社区项目的 Stars 或 Demo 结果当作准确率保证。
