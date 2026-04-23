const { app, BrowserWindow, ipcMain, globalShortcut, screen } = require('electron')
const path = require('path')
const WebSocket = require('ws')

let mainWindow = null
let ws = null
let reconnectTimer = null

const WS_URL = 'ws://localhost:8765'
const RECONNECT_DELAY = 3000

function createWindow() {
  const { width } = screen.getPrimaryDisplay().workAreaSize

  mainWindow = new BrowserWindow({
    width: 800,
    height: 140,
    x: Math.floor((width - 800) / 2),
    y: 0,
    frame: false,
    transparent: true,
    resizable: false,
    skipTaskbar: true,
    hasShadow: false,
    webPreferences: {
      preload: path.join(__dirname, '../../preload/preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  mainWindow.setAlwaysOnTop(true, 'screen-saver')
  mainWindow.setContentProtection(true)
  mainWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true })

  if (app.isPackaged) {
    mainWindow.loadFile(path.join(__dirname, '../../../dist/index.html'))
  } else {
    mainWindow.loadURL('http://localhost:5173')
  }
}

function connectWebSocket() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return

  ws = new WebSocket(WS_URL)

  ws.on('open', () => {
    clearTimeout(reconnectTimer)
    if (mainWindow) mainWindow.webContents.send('bridge-status', { connected: true })
  })

  ws.on('message', (data) => {
    try {
      const msg = JSON.parse(data.toString())
      if (!mainWindow) return

      switch (msg.type) {
        case 'transcript':
          mainWindow.webContents.send('transcript-update', msg.text)
          break
        case 'suggestion':
          mainWindow.webContents.send('suggestion-update', msg.bullets)
          break
        case 'audio-level':
          mainWindow.webContents.send('audio-level', msg.level)
          break
        case 'status':
          mainWindow.webContents.send('toggle-listening', msg.capturing)
          break
        case 'error':
          console.error('[bridge error]', msg.message)
          break
      }
    } catch (e) {
      console.error('[ws parse error]', e)
    }
  })

  ws.on('close', () => {
    if (mainWindow) mainWindow.webContents.send('bridge-status', { connected: false })
    reconnectTimer = setTimeout(connectWebSocket, RECONNECT_DELAY)
  })

  ws.on('error', () => ws.terminate())
}

function sendCommand(command) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ command }))
    return { success: true }
  }
  return { success: false, error: 'Bridge not connected' }
}

app.whenReady().then(() => {
  createWindow()
  connectWebSocket()

  ipcMain.handle('start-listening', () => sendCommand('start'))
  ipcMain.handle('stop-listening', () => sendCommand('stop'))

  ipcMain.on('set-click-through', (_, enabled) => {
    if (mainWindow) mainWindow.setIgnoreMouseEvents(enabled, { forward: true })
  })

  ipcMain.on('hide-window', () => { if (mainWindow) mainWindow.hide() })
  ipcMain.on('show-window', () => { if (mainWindow) mainWindow.show() })

  globalShortcut.register('CommandOrControl+Shift+L', () => {
    if (mainWindow) mainWindow.webContents.send('toggle-listening', null)
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('will-quit', () => {
  globalShortcut.unregisterAll()
  if (ws) ws.terminate()
  clearTimeout(reconnectTimer)
})
