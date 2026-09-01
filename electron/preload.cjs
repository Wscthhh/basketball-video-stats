const { contextBridge } = require('electron')

const apiArgument = process.argv.find((value) => value.startsWith('--courttrace-api='))
contextBridge.exposeInMainWorld('courtTraceDesktop', { version: '0.1.0', apiBase: apiArgument?.slice('--courttrace-api='.length) || '' })
