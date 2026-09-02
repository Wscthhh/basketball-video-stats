const { contextBridge, ipcRenderer } = require('electron')

const apiArgument = process.argv.find((value) => value.startsWith('--courttrace-api='))
const mobileArgument = process.argv.find((value) => value.startsWith('--courttrace-mobile='))
const versionArgument = process.argv.find((value) => value.startsWith('--courttrace-version='))
contextBridge.exposeInMainWorld('courtTraceDesktop', {
  version: versionArgument?.slice('--courttrace-version='.length) || '0.1.3',
  apiBase: apiArgument?.slice('--courttrace-api='.length) || '',
  mobileUrl: mobileArgument?.slice('--courttrace-mobile='.length) || '',
  checkForUpdates: () => ipcRenderer.invoke('check-for-updates'),
  downloadUpdate: () => ipcRenderer.invoke('download-update'),
  installUpdate: () => ipcRenderer.invoke('install-update'),
  onUpdateStatus: (callback) => ipcRenderer.on('update-status', (_event, payload) => callback(payload)),
})
