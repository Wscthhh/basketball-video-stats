const { contextBridge } = require('electron')

const apiArgument = process.argv.find((value) => value.startsWith('--courttrace-api='))
const mobileArgument = process.argv.find((value) => value.startsWith('--courttrace-mobile='))
contextBridge.exposeInMainWorld('courtTraceDesktop', { version: '0.1.0', apiBase: apiArgument?.slice('--courttrace-api='.length) || '', mobileUrl: mobileArgument?.slice('--courttrace-mobile='.length) || '' })
