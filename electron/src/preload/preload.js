const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('closer', {
  startListening: () => ipcRenderer.invoke('start-listening'),
  stopListening: () => ipcRenderer.invoke('stop-listening'),
  setClickThrough: (enabled) => ipcRenderer.send('set-click-through', enabled),
  hideWindow: () => ipcRenderer.send('hide-window'),
  showWindow: () => ipcRenderer.send('show-window'),

  onTranscriptUpdate: (cb) => ipcRenderer.on('transcript-update', (_, text) => cb(text)),
  onSuggestionUpdate: (cb) => ipcRenderer.on('suggestion-update', (_, bullets) => cb(bullets)),
  onAudioLevel: (cb) => ipcRenderer.on('audio-level', (_, level) => cb(level)),
  onBridgeStatus: (cb) => ipcRenderer.on('bridge-status', (_, status) => cb(status)),
  onToggleListening: (cb) => ipcRenderer.on('toggle-listening', (_, isListening) => cb(isListening)),
})
