const { app, BrowserWindow, dialog, net } = require('electron')
const { spawn } = require('child_process')
const path = require('path')
const http = require('http')
const fs = require('fs')
const { execFile } = require('child_process')
const { autoUpdater } = require('electron-updater')

let backend
let backendPort = 8000
let runtimeRoot

function waitForBackend(port, attempts = 40) {
  return new Promise((resolve, reject) => {
    const check = () => {
      const request = http.get(`http://127.0.0.1:${port}/api/health`, (response) => {
        response.resume()
        if (response.statusCode === 200) return resolve()
        retry()
      })
      request.on('error', retry)
      request.setTimeout(800, () => { request.destroy(); retry() })
    }
    const retry = () => {
      if (attempts-- <= 0) reject(new Error('后端服务启动超时'))
      else setTimeout(check, 250)
    }
    check()
  })
}

function startBackend() {
  const resourceRoot = app.isPackaged ? runtimeRoot : path.join(__dirname, '..')
  const executable = app.isPackaged ? path.join(resourceRoot, 'backend', 'CourtTraceBackend', 'CourtTraceBackend.exe') : null
  const args = executable ? ['--port', String(backendPort)] : ['-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', String(backendPort)]
  const ffmpegRoot = app.isPackaged ? path.join(resourceRoot, 'ffmpeg') : ''
  backend = spawn(executable || process.env.COURTTRACE_PYTHON || 'python', args, {
    cwd: resourceRoot,
    env: { ...process.env, PATH: ffmpegRoot ? `${ffmpegRoot}${path.delimiter}${process.env.PATH || ''}` : process.env.PATH, COURTTRACE_APP_ROOT: resourceRoot, COURTTRACE_DATA_DIR: path.join(app.getPath('userData'), 'data') },
    windowsHide: true,
    stdio: 'ignore',
  })
  backend.on('exit', (code) => { if (code && app.isReady()) dialog.showErrorBox('COURTTRACE 后端已退出', `服务退出代码：${code}`) })
}

function runtimeReady() {
  const root = path.join(app.getPath('userData'), 'runtime')
  return fs.existsSync(path.join(root, 'backend', 'CourtTraceBackend', 'CourtTraceBackend.exe')) && fs.existsSync(path.join(root, 'ffmpeg', 'ffmpeg.exe')) && fs.existsSync(path.join(root, 'models', 'player_detector.pt'))
}

function downloadRuntime(url, target) {
  return new Promise((resolve, reject) => {
    fs.mkdirSync(target, { recursive: true })
    const archive = path.join(app.getPath('temp'), 'courttrace-runtime.zip')
    const file = fs.createWriteStream(archive)
    const request = net.request(url)
    request.on('response', (response) => {
      if (response.statusCode < 200 || response.statusCode >= 300) return reject(new Error(`Runtime 下载失败：HTTP ${response.statusCode}`))
      response.pipe(file)
      file.on('finish', () => file.close(() => execFile('tar', ['-xf', archive, '-C', target], (error) => { fs.rmSync(archive, { force: true }); error ? reject(error) : resolve() })))
    })
    request.on('error', reject)
    request.end()
  })
}

async function ensureRuntime() {
  if (!app.isPackaged || runtimeReady()) { runtimeRoot = app.isPackaged ? path.join(app.getPath('userData'), 'runtime') : path.join(__dirname, '..'); return true }
  const url = process.env.COURTTRACE_RUNTIME_URL || 'https://github.com/Wscthhh/basketball-video-stats/releases/download/v0.1.0/CourtTrace-Runtime-0.1.0.zip'
  if (!url) {
    dialog.showErrorBox('COURTTRACE 需要运行环境', '首次启动需要下载独立 Runtime。请配置 COURTTRACE_RUNTIME_URL，或先安装 Runtime 包。')
    return false
  }
  try { await downloadRuntime(url, path.join(app.getPath('userData'), 'runtime')); runtimeRoot = path.join(app.getPath('userData'), 'runtime'); return true } catch (error) { dialog.showErrorBox('Runtime 下载失败', error.message); return false }
}

async function createWindow() {
  if (!await ensureRuntime()) { app.quit(); return }
  startBackend()
  try { await waitForBackend(backendPort) } catch (error) { dialog.showErrorBox('COURTTRACE 启动失败', error.message); app.quit(); return }
  const window = new BrowserWindow({ width: 1440, height: 920, minWidth: 1000, minHeight: 700, webPreferences: { preload: path.join(__dirname, 'preload.cjs'), contextIsolation: true, sandbox: true, additionalArguments: [`--courttrace-api=http://127.0.0.1:${backendPort}`] } })
  const indexPath = app.isPackaged ? path.join(__dirname, '..', 'dist', 'index.html') : path.join(__dirname, '..', 'dist', 'index.html')
  try {
    await window.loadFile(indexPath)
  } catch (error) {
    dialog.showErrorBox('COURTTRACE 加载失败', error.message)
    window.destroy()
    app.quit()
  }
}

app.whenReady().then(createWindow)
app.whenReady().then(() => { if (app.isPackaged) { autoUpdater.checkForUpdatesAndNotify().catch(() => undefined) } })
app.on('window-all-closed', () => { if (backend) backend.kill(); if (process.platform !== 'darwin') app.quit() })
app.on('before-quit', () => { if (backend) backend.kill() })
