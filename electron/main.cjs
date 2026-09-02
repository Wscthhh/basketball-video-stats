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
let startupRunning = false
let backendEnvironment
const lanToken = crypto.randomBytes(24).toString('hex')
const requiredRuntimeVersion = '0.1.1'

function lanAddress() {
  const interfaces = os.networkInterfaces()
  const addresses = Object.values(interfaces).flatMap((entries) => entries || []).filter((entry) => entry.family === 'IPv4' && !entry.internal && !entry.address.startsWith('169.254.'))
  return addresses.find((entry) => /^192\.168\.|^10\.|^172\.(1[6-9]|2\d|3[01])\./.test(entry.address))?.address || addresses[0]?.address || '127.0.0.1'
}

function installedRuntimePath() {
  return path.join(process.env.LOCALAPPDATA || app.getPath('userData'), 'COURTTRACE', 'runtime')
}

function pathExists(filePath) {
  try { return fs.existsSync(filePath) } catch (_) { return false }
}

function execFileResult(file, args, options = {}) {
  return new Promise((resolve) => {
    execFile(file, args, { windowsHide: true, timeout: 30000, ...options }, (error, stdout, stderr) => resolve({ ok: !error, stdout: String(stdout || '').trim(), stderr: String(stderr || '').trim() }))
  })
}

function configuredEnvironment() {
  try {
    const value = JSON.parse(fs.readFileSync(path.join(app.getPath('userData'), 'desktop-config.json'), 'utf8'))
    return value.python && value.appRoot ? value : null
  } catch (_) { return null }
}

async function candidateProjectRoots() {
  const roots = new Set()
  const configured = configuredEnvironment()
  if (configured?.appRoot) roots.add(configured.appRoot)
  if (process.env.COURTTRACE_APP_ROOT) roots.add(process.env.COURTTRACE_APP_ROOT)
  roots.add(process.cwd())
  roots.add(path.join(app.getPath('documents'), 'basketball-video-stats'))
  roots.add(path.join(app.getPath('desktop'), 'basketball-video-stats'))
  if (process.platform === 'win32') {
    const drives = await execFileResult('powershell.exe', ['-NoProfile', '-Command', '(Get-PSDrive -PSProvider FileSystem).Root'])
    for (const drive of drives.stdout.split(/\r?\n/).filter(Boolean)) roots.add(path.join(drive, 'basketball-video-stats'))
  }
  return [...roots]
}

async function validateExistingEnvironment(root) {
  const configured = configuredEnvironment()
  if (!pathExists(path.join(root, 'backend', 'main.py'))) return null
  const systemPython = await execFileResult('where.exe', ['python.exe'])
  const pythonCandidates = [...new Set([configured?.appRoot === root ? configured.python : '', process.env.COURTTRACE_PYTHON || '', path.join(root, '.venv', 'Scripts', 'python.exe'), ...systemPython.stdout.split(/\r?\n/)].filter(Boolean))]
  const models = ['player_detector.pt', 'ball_detector_model.pt', 'court_keypoint_detector.pt']
  if (!models.every((name) => pathExists(path.join(root, 'models', name)))) return null
  const ffmpeg = await execFileResult('where.exe', ['ffmpeg.exe'])
  if (!ffmpeg.ok) return null
  for (const python of pythonCandidates.filter(pathExists)) {
    const probe = await execFileResult(python, ['-c', "import sys,fastapi,uvicorn,torch,ultralytics,cv2; print(f'{sys.version_info.major}.{sys.version_info.minor}|{int(torch.cuda.is_available())}')"], { cwd: root })
    if (/^(3\.11|3\.12)\|[01]$/.test(probe.stdout)) return { type: 'python', python, appRoot: root, ffmpegDir: path.dirname(ffmpeg.stdout.split(/\r?\n/)[0]), details: probe.stdout }
  }
  return null
}

async function findExistingEnvironment() {
  sendRuntimeStatus({ stage: '正在检测现有 AI 环境', percent: 3, detail: '检查 Python、PyTorch、FFmpeg 和模型文件。' })
  for (const root of await candidateProjectRoots()) {
    const environment = await validateExistingEnvironment(root)
    if (environment) {
      log(`Using existing environment: ${environment.python}, root=${environment.appRoot}, probe=${environment.details}`)
      try { fs.writeFileSync(path.join(app.getPath('userData'), 'desktop-config.json'), JSON.stringify({ python: environment.python, appRoot: environment.appRoot }, null, 2)) } catch (_) {}
      sendRuntimeStatus({ stage: '检测到可用的本地环境', percent: 100, detail: environment.appRoot })
      return environment
    }
  }
  log('No compatible existing environment found')
  return null
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
  const environment = backendEnvironment || { type: 'python', python: process.env.COURTTRACE_PYTHON || 'python', appRoot: path.join(__dirname, '..'), ffmpegDir: '' }
  const executable = environment.type === 'runtime' ? path.join(environment.appRoot, 'backend', 'CourtTraceBackend', 'CourtTraceBackend.exe') : environment.python
  const args = environment.type === 'runtime' ? ['--host', '0.0.0.0', '--port', String(backendPort)] : ['-m', 'uvicorn', 'backend.main:app', '--host', '0.0.0.0', '--port', String(backendPort)]
  const ffmpegRoot = environment.ffmpegDir || ''
  log(`Starting backend: ${executable} in ${environment.appRoot}`)
  backend = spawn(executable, args, {
    cwd: environment.appRoot,
    env: { ...process.env, PATH: ffmpegRoot ? `${ffmpegRoot}${path.delimiter}${process.env.PATH || ''}` : process.env.PATH, COURTTRACE_APP_ROOT: environment.appRoot, COURTTRACE_DATA_DIR: path.join(app.getPath('userData'), 'data'), COURTTRACE_HOST: '0.0.0.0', COURTTRACE_LAN_TOKEN: lanToken },
    windowsHide: true,
    stdio: 'ignore',
  })
  backend.on('error', (error) => { log(`Backend spawn error: ${error.message}`); dialog.showErrorBox('COURTTRACE 后端启动失败', error.message) })
  backend.on('exit', (code) => { log(`Backend exited: ${code}`); if (code && app.isReady()) dialog.showErrorBox('COURTTRACE 后端已退出', `服务退出代码：${code}`) })
}

function ensureFirewallRule() {
  if (process.platform !== 'win32' || !app.isPackaged || process.env.COURTTRACE_SKIP_FIREWALL === '1') return Promise.resolve()
  const executable = backendEnvironment?.type === 'python' ? backendEnvironment.python : path.join(runtimeRoot, 'backend', 'CourtTraceBackend', 'CourtTraceBackend.exe')
  return new Promise((resolve) => {
    execFile('powershell.exe', ['-NoProfile', '-Command', "if (Get-NetFirewallRule -DisplayName 'COURTTRACE Mobile Upload' -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"], (error) => {
      if (!error) return resolve()
      const args = `advfirewall firewall add rule name="COURTTRACE Mobile Upload" dir=in action=allow program="${executable}" protocol=TCP localport=8000 profile=private,public enable=yes`
      execFile('powershell.exe', ['-NoProfile', '-WindowStyle', 'Hidden', '-Command', `Start-Process -FilePath netsh.exe -ArgumentList '${args.replaceAll("'", "''")}' -Verb RunAs -Wait`], (elevatedError) => {
        log(elevatedError ? `Firewall rule was not added: ${elevatedError.message}` : 'Firewall rule added')
        resolve()
      })
    })
  })
}

function runtimeReady() {
  const root = installedRuntimePath()
  let version = ''
  try { version = JSON.parse(fs.readFileSync(path.join(root, 'version.json'), 'utf8')).version || '' } catch (_) {}
  const ready = version === requiredRuntimeVersion && fs.existsSync(path.join(root, 'backend', 'CourtTraceBackend', 'CourtTraceBackend.exe')) && fs.existsSync(path.join(root, 'ffmpeg', 'ffmpeg.exe')) && fs.existsSync(path.join(root, 'models', 'player_detector.pt'))
  log(`Runtime check: ${root}, version=${version || 'legacy'}, required=${requiredRuntimeVersion}, ready=${ready}`)
  return ready
}

function sendRuntimeStatus(payload) {
  mainWindow?.webContents.send('runtime-status', payload)
}

function hashFile(filePath) {
  return new Promise((resolve, reject) => {
    const hash = crypto.createHash('sha256')
    const input = fs.createReadStream(filePath)
    input.on('data', (chunk) => hash.update(chunk))
    input.on('end', () => resolve(hash.digest('hex').toLowerCase()))
    input.on('error', reject)
  })
}

function downloadFile(url, destination, onProgress = () => {}) {
  return new Promise((resolve, reject) => {
    const partial = `${destination}.part`
    const existing = fs.existsSync(partial) ? fs.statSync(partial).size : 0
    const request = net.request(url)
    if (existing) request.setHeader('Range', `bytes=${existing}-`)
    request.on('response', (response) => {
      if (response.statusCode < 200 || response.statusCode >= 300) return reject(new Error(`Runtime 下载失败：HTTP ${response.statusCode}`))
      const append = response.statusCode === 206 && existing > 0
      const offset = append ? existing : 0
      if (!append && existing) fs.rmSync(partial, { force: true })
      const total = offset + Number(response.headers['content-length'] || 0)
      const file = fs.createWriteStream(partial, { flags: append ? 'a' : 'w' })
      let received = offset
      let lastBytes = received
      let lastTime = Date.now()
      response.on('data', (chunk) => {
        received += chunk.length
        file.write(chunk)
        const now = Date.now()
        if (now - lastTime >= 500) {
          onProgress({ received, total, speed: (received - lastBytes) / ((now - lastTime) / 1000) })
          lastBytes = received
          lastTime = now
        }
      })
      response.on('end', () => file.end(() => { fs.rmSync(destination, { force: true }); fs.renameSync(partial, destination); onProgress({ received, total, speed: 0 }); resolve() }))
      response.on('error', (error) => { file.close(); reject(error) })
      file.on('error', reject)
    })
    request.on('error', reject)
    request.end()
  })
}

async function downloadRuntime(url, target) {
  fs.mkdirSync(target, { recursive: true })
  const manifestPath = path.join(app.getPath('temp'), 'courttrace-runtime.json')
  sendRuntimeStatus({ stage: '正在获取 Runtime 清单', percent: 1 })
  await downloadFile(url, manifestPath)
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'))
  const toolsRoot = app.isPackaged ? path.join(process.resourcesPath, 'tools') : path.join(__dirname, '..', 'node_modules', '7zip-bin', 'win', 'x64')
  const extractor = path.join(toolsRoot, '7za.exe')
  const prefix = path.join(app.getPath('temp'), 'CourtTrace-Runtime.7z')
  for (let index = 0; index < manifest.parts.length; index += 1) {
    const part = manifest.parts[index]
    const partPath = `${prefix}.${String(part.index).padStart(3, '0')}`
    if (fs.existsSync(partPath) && part.sha256 && await hashFile(partPath) === part.sha256.toLowerCase()) {
      sendRuntimeStatus({ stage: `分卷 ${index + 1}/${manifest.parts.length} 已校验`, percent: ((index + 1) / manifest.parts.length) * 88 })
      continue
    }
    fs.rmSync(partPath, { force: true })
    await downloadFile(new URL(part.name, url).toString(), partPath, ({ received, total, speed }) => {
      const partProgress = total ? received / total : 0
      const percent = ((index + partProgress) / manifest.parts.length) * 88
      const mb = (received / 1024 / 1024).toFixed(0)
      const totalMb = total ? (total / 1024 / 1024).toFixed(0) : '--'
      const speedMb = speed ? `${(speed / 1024 / 1024).toFixed(1)} MB/s` : ''
      sendRuntimeStatus({ stage: `正在下载 Runtime 分卷 ${index + 1}/${manifest.parts.length}`, percent, detail: `${mb} MB / ${totalMb} MB${speedMb ? ` · ${speedMb}` : ''}` })
    })
    sendRuntimeStatus({ stage: `正在校验分卷 ${index + 1}/${manifest.parts.length}`, percent: ((index + 1) / manifest.parts.length) * 88 })
    const hash = await hashFile(partPath)
    if (part.sha256 && hash !== part.sha256.toLowerCase()) throw new Error(`Runtime 分卷校验失败：${part.name}`)
  }
  sendRuntimeStatus({ stage: '正在解压 Runtime', percent: 92, detail: '解压过程可能需要几分钟，请勿关闭应用。' })
  await new Promise((resolve, reject) => execFile(extractor, ['x', `${prefix}.001`, `-o${target}`, '-y'], (error) => error ? reject(error) : resolve()))
  for (const part of manifest.parts) fs.rmSync(`${prefix}.${String(part.index).padStart(3, '0')}`, { force: true })
  fs.rmSync(manifestPath, { force: true })
  sendRuntimeStatus({ stage: 'Runtime 准备完成', percent: 100 })
}

async function ensureRuntime() {
  const installedRuntime = installedRuntimePath()
  if (!app.isPackaged) { backendEnvironment = { type: 'python', python: process.env.COURTTRACE_PYTHON || path.join(__dirname, '..', '.venv', 'Scripts', 'python.exe'), appRoot: path.join(__dirname, '..'), ffmpegDir: '' }; return true }
  if (runtimeReady()) { runtimeRoot = installedRuntime; backendEnvironment = { type: 'runtime', appRoot: installedRuntime, ffmpegDir: path.join(installedRuntime, 'ffmpeg') }; log(`Using runtime: ${runtimeRoot}`); return true }
  const existing = await findExistingEnvironment()
  if (existing) { backendEnvironment = existing; runtimeRoot = existing.appRoot; return true }
  const url = process.env.COURTTRACE_RUNTIME_URL || 'https://github.com/Wscthhh/basketball-video-stats/releases/download/runtime-v0.1.1/CourtTrace-Runtime-0.1.1.json'
  if (!url) {
    dialog.showErrorBox('COURTTRACE 需要运行环境', '首次启动需要下载独立 Runtime。请配置 COURTTRACE_RUNTIME_URL，或先安装 Runtime 包。')
    return false
  }
  log(`Runtime missing, downloading from ${url}`)
  try { await downloadRuntime(url, installedRuntime); runtimeRoot = installedRuntime; backendEnvironment = { type: 'runtime', appRoot: installedRuntime, ffmpegDir: path.join(installedRuntime, 'ffmpeg') }; log(`Runtime downloaded: ${runtimeRoot}`); return true } catch (error) { log(`Runtime download failed: ${error.message}`); sendRuntimeStatus({ status: 'error', stage: 'Runtime 下载失败', message: '请检查网络连接后重试。', detail: error.message }); return false }
}

async function completeStartup(window) {
  if (startupRunning) return
  startupRunning = true
  if (!await ensureRuntime()) { startupRunning = false; return }
  await ensureFirewallRule()
  sendRuntimeStatus({ stage: '正在启动本地分析服务', percent: 100 })
  startBackend()
  try { await waitForBackend(backendPort) } catch (error) { log(`Backend startup timeout: ${error.message}`); sendRuntimeStatus({ status: 'error', stage: '分析服务启动失败', message: '本地分析服务未能正常启动。', detail: error.message }); startupRunning = false; return }
  const indexPath = app.isPackaged ? path.join(__dirname, '..', 'dist', 'index.html') : path.join(__dirname, '..', 'dist', 'index.html')
  try {
    await window.loadFile(indexPath)
    startupRunning = false
  } catch (error) {
    dialog.showErrorBox('COURTTRACE 加载失败', error.message)
    window.destroy()
    app.quit()
  }
}

async function createWindow() {
  const mobileUrl = `http://${lanAddress()}:${backendPort}/mobile?token=${lanToken}`
  const window = new BrowserWindow({ width: 1440, height: 920, minWidth: 1000, minHeight: 700, show: false, webPreferences: { preload: path.join(__dirname, 'preload.cjs'), contextIsolation: true, sandbox: true, additionalArguments: [`--courttrace-api=http://127.0.0.1:${backendPort}`, `--courttrace-mobile=${mobileUrl}`, `--courttrace-version=${app.getVersion()}`] } })
  mainWindow = window
  await window.loadFile(path.join(__dirname, 'loading.html'))
  window.show()
  log('Desktop window created')
  void completeStartup(window)
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
ipcMain.handle('retry-runtime', async () => {
  if (backend && !backend.killed) backend.kill()
  await completeStartup(mainWindow)
  return { status: 'retrying' }
})

const hasSingleInstanceLock = app.requestSingleInstanceLock()
if (!hasSingleInstanceLock) {
  app.quit()
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.show()
      mainWindow.focus()
    }
  })
  app.whenReady().then(createWindow)
  app.whenReady().then(() => { if (app.isPackaged) { autoUpdater.checkForUpdates().catch(() => undefined) } })
}
app.on('window-all-closed', () => { if (backend) backend.kill(); if (process.platform !== 'darwin') app.quit() })
app.on('before-quit', () => { if (backend) backend.kill() })
process.on('uncaughtException', (error) => { log(`Uncaught exception: ${error.stack || error.message}`); dialog.showErrorBox('COURTTRACE 启动错误', error.message) })
process.on('unhandledRejection', (error) => { log(`Unhandled rejection: ${error && (error.stack || error.message)}`) })
