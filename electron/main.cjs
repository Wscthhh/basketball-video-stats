const { app, BrowserWindow, dialog, net, ipcMain } = require('electron')
const { spawn } = require('child_process')
const path = require('path')
const http = require('http')
const fs = require('fs')
const { execFile } = require('child_process')
const { autoUpdater } = require('electron-updater')
const crypto = require('crypto')
const os = require('os')

let backend
let backendPort = 8000
let runtimeRoot
let mainWindow
let manualUpdateCheck = false
const lanToken = crypto.randomBytes(24).toString('hex')

function lanAddress() {
  const interfaces = os.networkInterfaces()
  for (const entries of Object.values(interfaces)) for (const entry of entries || []) if (entry.family === 'IPv4' && !entry.internal) return entry.address
  return '127.0.0.1'
}

function installedRuntimePath() {
  return path.join(process.env.LOCALAPPDATA || app.getPath('userData'), 'COURTTRACE', 'runtime')
}

function log(message) {
  try { fs.appendFileSync(path.join(app.getPath('userData'), 'desktop.log'), `[${new Date().toISOString()}] ${message}\n`) } catch (_) {}
}

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
  log(`Starting backend: ${executable || 'python'} in ${resourceRoot}`)
  backend = spawn(executable || process.env.COURTTRACE_PYTHON || 'python', args, {
    cwd: resourceRoot,
    env: { ...process.env, PATH: ffmpegRoot ? `${ffmpegRoot}${path.delimiter}${process.env.PATH || ''}` : process.env.PATH, COURTTRACE_APP_ROOT: resourceRoot, COURTTRACE_DATA_DIR: path.join(app.getPath('userData'), 'data'), COURTTRACE_HOST: '0.0.0.0', COURTTRACE_LAN_TOKEN: lanToken },
    windowsHide: true,
    stdio: 'ignore',
  })
  backend.on('error', (error) => { log(`Backend spawn error: ${error.message}`); dialog.showErrorBox('COURTTRACE 后端启动失败', error.message) })
  backend.on('exit', (code) => { log(`Backend exited: ${code}`); if (code && app.isReady()) dialog.showErrorBox('COURTTRACE 后端已退出', `服务退出代码：${code}`) })
}

function runtimeReady() {
  const root = installedRuntimePath()
  const ready = fs.existsSync(path.join(root, 'backend', 'CourtTraceBackend', 'CourtTraceBackend.exe')) && fs.existsSync(path.join(root, 'ffmpeg', 'ffmpeg.exe')) && fs.existsSync(path.join(root, 'models', 'player_detector.pt'))
  log(`Runtime check: ${root}, ready=${ready}`)
  return ready
}

function downloadFile(url, destination) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(destination)
    const request = net.request(url)
    request.on('response', (response) => {
      if (response.statusCode < 200 || response.statusCode >= 300) return reject(new Error(`Runtime 下载失败：HTTP ${response.statusCode}`))
      response.pipe(file)
      file.on('finish', () => file.close(resolve))
    })
    request.on('error', reject)
    request.end()
  })
}

async function downloadRuntime(url, target) {
  fs.mkdirSync(target, { recursive: true })
  const manifestPath = path.join(app.getPath('temp'), 'courttrace-runtime.json')
  await downloadFile(url, manifestPath)
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'))
  const toolsRoot = app.isPackaged ? path.join(process.resourcesPath, 'tools') : path.join(__dirname, '..', 'node_modules', '7zip-bin', 'win', 'x64')
  const extractor = path.join(toolsRoot, '7za.exe')
  const prefix = path.join(app.getPath('temp'), 'CourtTrace-Runtime.7z')
  for (const part of manifest.parts) {
    const partPath = `${prefix}.${String(part.index).padStart(3, '0')}`
    await downloadFile(new URL(part.name, url).toString(), partPath)
    const hash = crypto.createHash('sha256').update(fs.readFileSync(partPath)).digest('hex').toLowerCase()
    if (part.sha256 && hash !== part.sha256.toLowerCase()) throw new Error(`Runtime 分卷校验失败：${part.name}`)
  }
  await new Promise((resolve, reject) => execFile(extractor, ['x', `${prefix}.001`, `-o${target}`, '-y'], (error) => error ? reject(error) : resolve()))
  for (const part of manifest.parts) fs.rmSync(`${prefix}.${String(part.index).padStart(3, '0')}`, { force: true })
  fs.rmSync(manifestPath, { force: true })
}

async function ensureRuntime() {
  const installedRuntime = installedRuntimePath()
  if (!app.isPackaged || runtimeReady()) { runtimeRoot = app.isPackaged ? installedRuntime : path.join(__dirname, '..'); log(`Using runtime: ${runtimeRoot}`); return true }
  const url = process.env.COURTTRACE_RUNTIME_URL || 'https://github.com/Wscthhh/basketball-video-stats/releases/download/runtime-v0.1.0/CourtTrace-Runtime-0.1.0.json'
  if (!url) {
    dialog.showErrorBox('COURTTRACE 需要运行环境', '首次启动需要下载独立 Runtime。请配置 COURTTRACE_RUNTIME_URL，或先安装 Runtime 包。')
    return false
  }
  log(`Runtime missing, downloading from ${url}`)
  try { await downloadRuntime(url, installedRuntime); runtimeRoot = installedRuntime; log(`Runtime downloaded: ${runtimeRoot}`); return true } catch (error) { log(`Runtime download failed: ${error.message}`); dialog.showErrorBox('Runtime 下载失败', error.message); return false }
}

async function createWindow() {
  const mobileUrl = `http://${lanAddress()}:${backendPort}/mobile?token=${lanToken}`
  const window = new BrowserWindow({ width: 1440, height: 920, minWidth: 1000, minHeight: 700, webPreferences: { preload: path.join(__dirname, 'preload.cjs'), contextIsolation: true, sandbox: true, additionalArguments: [`--courttrace-api=http://127.0.0.1:${backendPort}`, `--courttrace-mobile=${mobileUrl}`, `--courttrace-version=${app.getVersion()}`] } })
  mainWindow = window
  window.show()
  log('Desktop window created')
  if (!await ensureRuntime()) { window.destroy(); app.quit(); return }
  startBackend()
  try { await waitForBackend(backendPort) } catch (error) { log(`Backend startup timeout: ${error.message}`); dialog.showErrorBox('COURTTRACE 启动失败', error.message); window.destroy(); app.quit(); return }
  const indexPath = app.isPackaged ? path.join(__dirname, '..', 'dist', 'index.html') : path.join(__dirname, '..', 'dist', 'index.html')
  try {
    await window.loadFile(indexPath)
  } catch (error) {
    dialog.showErrorBox('COURTTRACE 加载失败', error.message)
    window.destroy()
    app.quit()
  }
}

function sendUpdateStatus(status, payload = {}) {
  mainWindow?.webContents.send('update-status', { status, ...payload })
}

autoUpdater.autoDownload = false
autoUpdater.on('checking-for-update', () => sendUpdateStatus('checking'))
autoUpdater.on('update-available', async (info) => {
  sendUpdateStatus('available', { version: info.version })
  if (manualUpdateCheck) {
    const result = await dialog.showMessageBox(mainWindow, { type: 'info', title: '发现新版本', message: `最新版本为 v${info.version}，当前版本为 v${app.getVersion()}。`, detail: '是否立即下载更新？', buttons: ['下载更新', '暂不更新'], defaultId: 0, cancelId: 1 })
    if (result.response === 0) await autoUpdater.downloadUpdate()
    manualUpdateCheck = false
  }
})
autoUpdater.on('update-not-available', () => sendUpdateStatus('latest', { version: app.getVersion() }))
autoUpdater.on('download-progress', (info) => sendUpdateStatus('downloading', { percent: info.percent }))
autoUpdater.on('update-downloaded', (info) => sendUpdateStatus('downloaded', { version: info.version }))
autoUpdater.on('error', (error) => sendUpdateStatus('error', { message: error.message.includes('404') || error.message.includes('releases.atom') ? 'GitHub Release 更新源不可访问（HTTP 404），请确认仓库和 Release 对客户端公开。' : error.message }))
ipcMain.handle('check-for-updates', async () => {
  if (!app.isPackaged) return { status: 'development' }
  manualUpdateCheck = true
  try { await autoUpdater.checkForUpdates() } catch (error) { sendUpdateStatus('error', { message: error.message }); throw error }
  return { status: 'checking' }
})
ipcMain.handle('download-update', async () => { await autoUpdater.downloadUpdate(); return { status: 'downloading' } })
ipcMain.handle('install-update', () => { autoUpdater.quitAndInstall(); return { status: 'installing' } })

app.whenReady().then(createWindow)
app.whenReady().then(() => { if (app.isPackaged) { autoUpdater.checkForUpdates().catch(() => undefined) } })
app.on('window-all-closed', () => { if (backend) backend.kill(); if (process.platform !== 'darwin') app.quit() })
app.on('before-quit', () => { if (backend) backend.kill() })
process.on('uncaughtException', (error) => { log(`Uncaught exception: ${error.stack || error.message}`); dialog.showErrorBox('COURTTRACE 启动错误', error.message) })
process.on('unhandledRejection', (error) => { log(`Unhandled rejection: ${error && (error.stack || error.message)}`) })
