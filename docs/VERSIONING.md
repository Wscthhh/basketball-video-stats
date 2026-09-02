# COURTTRACE 版本更新约定

## 版本号

项目使用语义化版本号：

```text
MAJOR.MINOR.PATCH
```

- `PATCH`：修复问题、性能优化、界面小调整，不改变数据结构和使用方式。
- `MINOR`：增加向后兼容的新功能。
- `MAJOR`：存在不兼容的数据、接口或 Runtime 变更。

示例：

```text
0.1.0 -> 0.1.1  修复白屏、修复上传问题
0.1.1 -> 0.2.0  增加手机上传或新的分析功能
0.2.0 -> 1.0.0  正式稳定版本，可能包含迁移要求
```

## 发布应用更新

普通代码发布只更新 Electron/Vue 应用层，不重新打包 Runtime、FFmpeg、Torch 或模型。

```powershell
npm version patch
git push origin main --follow-tags
```

GitHub Actions 检测到 `v*.*.*` tag 后会自动：

- 安装 Node 依赖
- 构建 Vue 前端
- 构建 Electron NSIS 安装包
- 生成 `latest.yml` 和 `.blockmap`
- 创建 GitHub Release
- 上传应用更新文件

已安装的旧版 COURTTRACE 会在启动时通过 `electron-updater` 检查新版本。应用更新不会删除：

- 比赛数据
- 原始视频
- 人工训练样本
- Runtime
- 模型文件

## Runtime 更新

Runtime 单独维护版本，不随普通应用更新重复下载：

```text
%LOCALAPPDATA%\COURTTRACE\runtime
```

桌面端在下载 Runtime 前会检查用户配置、`COURTTRACE_APP_ROOT` / `COURTTRACE_PYTHON`、项目目录 `.venv` 和系统 Python。只有 Python 3.11/3.12、核心依赖、FFmpeg、后端源码与三个模型全部可用时才复用现有环境；环境不完整时必须回退标准 Runtime，不能仅凭 `python.exe` 存在就跳过安装。

只有 Python 依赖、FFmpeg、Torch 或后端兼容性发生变化时，才发布新的 Runtime 安装包。

Runtime 版本发生变化时，必须同步更新：

- `scripts/build-runtime.ps1`
- `installer/courttrace-runtime.iss`
- Runtime 安装包文件名
- 应用需要的最低 Runtime 版本

## 模型更新

模型更新独立于应用和 Runtime。替换模型前必须：

- 保存模型版本号
- 记录 SHA-256
- 验证模型可以加载
- 保留上一版模型用于回滚

## 发布前检查

```powershell
npm run build
& '.venv\Scripts\python.exe' -m unittest discover -s backend -p 'test*.py' -v
node --check electron\main.cjs
```

发布前确认：

- 版本号已经递增
- Git tag 与 `package.json` 版本一致
- GitHub Release 资产包含 `latest.yml`
- 应用安装包没有包含 Runtime 和用户数据
- 已安装旧版可以检测到新版本
- 更新后比赛数据仍然存在

## 回滚

发现严重问题时：

1. 暂停当前 GitHub Release 的推广。
2. 保留旧版本 Release，不删除旧安装包。
3. 修复问题并发布更高的 `PATCH` 版本。
4. 不复用已发布的版本号和 tag。

禁止使用相同版本号覆盖已经发布的安装包。
