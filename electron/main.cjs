const { app, BrowserWindow, dialog } = require('electron')
const { spawn } = require('child_process')
const path = require('path')
const http = require('http')

let backend
let backendPort = 8000

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
  const resourceRoot = app.isPackaged ? process.resourcesPath : path.join(__dirname, '..')
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

async function createWindow() {
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
app.on('window-all-closed', () => { if (backend) backend.kill(); if (process.platform !== 'darwin') app.quit() })
app.on('before-quit', () => { if (backend) backend.kill() })
