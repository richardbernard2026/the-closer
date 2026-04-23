# CLAUDE.md — The Closer: AI Interview Copilot

## What This Project Is
A transparent, always-on-top Electron desktop app (Mac + Windows) that acts as a
stealth interview copilot. It captures system audio, transcribes it via Whisper,
and feeds GPT-4o suggestions as 5-word trigger phrases into a HUD the interviewer
cannot see on screen share.

---

## Stack — Do Not Deviate
| Layer | Technology |
|---|---|
| Desktop shell | Electron 25 |
| UI framework | React 18 + Vite 4 |
| Styling | Tailwind CSS 3 (utility classes only, no custom CSS frameworks) |
| Audio bridge | Python 3.11 + FastAPI + uvicorn |
| IPC | Electron contextBridge (contextIsolation: true, no nodeIntegration) |
| AI | OpenAI SDK — Whisper for STT, GPT-4o for suggestions |
| Transport | WebSocket (ws://localhost:8765) between Electron and Python |

**Never suggest replacing any of these with alternatives unless explicitly asked.**

---

## Project Structure — Do Not Reorganize
```
the-closer/
├── electron/
│   ├── src/
│   │   ├── main/index.js          ← Electron main process ONLY
│   │   ├── preload/preload.js     ← contextBridge ONLY, no logic
│   │   └── renderer/
│   │       ├── App.jsx
│   │       ├── main.jsx
│   │       ├── index.css
│   │       ├── hooks/
│   │       └── components/
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── package.json
├── python-bridge/
│   ├── bridge.py                  ← Single FastAPI file, keep it that way
│   ├── requirements.txt
│   └── .env                       ← Never commit this
├── CLAUDE.md                      ← This file
├── README.md
└── .gitignore
```

---

## Absolute Rules

### Never Do These Without Being Explicitly Asked
- Do not add new npm packages
- Do not add new Python packages
- Do not create new files outside the structure above
- Do not refactor working code "for cleanliness"
- Do not add comments to code that already has comments
- Do not run `npm run build` — dev mode only unless told otherwise
- Do not modify `.env` or print its contents anywhere
- Do not push to GitHub unless explicitly told to

### Always Do These
- Make the smallest change that fixes the problem
- Show diffs or changed lines, not entire files, when editing existing code
- Run `npm run dev` from `electron/` and `python bridge.py` from `python-bridge/`
- Use `source venv/bin/activate` before any Python commands
- Check if a port is in use before starting servers (lsof -i :8765, lsof -i :5173)

---

## How To Run (Two Terminals Required)

**Terminal 1 — Python Bridge:**
```bash
cd the-closer/python-bridge
source venv/bin/activate
python bridge.py
```
Expected: `INFO: Uvicorn running on http://127.0.0.1:8765`

**Terminal 2 — Electron:**
```bash
cd the-closer/electron
npm run dev
```
Expected: Vite ready + Electron window appears at top of screen

---

## Key Technical Decisions — Do Not Debate These

**Why `setContentProtection(true)`?**
Excludes window from macOS screen capture APIs and Windows WDA_EXCLUDEFROMCAPTURE.
This is a core feature. Do not remove it. It only works in built apps, not dev mode.

**Why `alwaysOnTop: 'screen-saver'`?**
Keeps HUD above fullscreen video calls. Lower levels get buried under Zoom/Meet.

**Why a separate Python process instead of Node audio?**
Node has no reliable cross-platform system audio loopback. Python + sounddevice
handles CoreAudio (macOS) and WASAPI (Windows) loopback consistently.

**Why WebSocket instead of Electron IPC for Python bridge?**
Python cannot use Electron IPC. WebSocket is the cleanest cross-process transport.

**Why contextIsolation: true with no nodeIntegration?**
Security. The renderer is treated as untrusted. All Node access goes through the
typed preload API only.

---

## IPC Contract — Do Not Change the API Shape

### Renderer → Main (via window.closer)
```js
window.closer.startListening()     → { success: bool, error?: string }
window.closer.stopListening()      → { success: bool }
window.closer.setClickThrough(bool)
window.closer.hideWindow()
window.closer.showWindow()
```

### Main → Renderer (event listeners)
```js
window.closer.onTranscriptUpdate(text => ...)
window.closer.onSuggestionUpdate(bullets => ...)   // bullets: string[]
window.closer.onAudioLevel(level => ...)           // level: 0.0–1.0
window.closer.onBridgeStatus({ connected: bool })
window.closer.onToggleListening(isListening => ...)
```

### WebSocket Message Format (Python ↔ Electron)
```json
// Electron → Python
{ "command": "start" }
{ "command": "stop" }

// Python → Electron
{ "type": "transcript", "text": "string" }
{ "type": "suggestion", "bullets": ["phrase 1", "phrase 2"] }
{ "type": "audio-level", "level": 0.0–1.0 }
{ "type": "status", "capturing": bool }
{ "type": "error", "message": "string" }
```

---

## GPT-4o Prompt Contract
The system prompt in `bridge.py` is intentional and tuned. Do not reword it.
Output must always be: `{ "bullets": ["3-5 word phrase", ...] }` — raw JSON, no markdown.
Max 3 bullets. Temperature 0.4. Max tokens 120.

---

## Environment Variables
```
OPENAI_API_KEY=sk-...    ← Required. Loaded from python-bridge/.env
```
Never hardcode keys. Never log them. Never include them in any output.

---

## Error Handling Priorities
1. Port conflicts (8765, 5173) — check first, kill if needed
2. Missing OPENAI_API_KEY — fail loudly with clear message, not a silent crash
3. No loopback audio device — warn clearly, fall back to default mic, log which device
4. WebSocket disconnects — Python auto-retries every 3s (already implemented)
5. Whisper failures — log and skip chunk, do not crash the bridge

---

## Git Discipline
- Commit message format: `type(scope): description`
  - e.g. `feat(hud): add waveform animation`, `fix(bridge): handle empty whisper response`
- Never commit: `node_modules/`, `dist/`, `venv/`, `.env`, `*.pyc`, `__pycache__/`
- Branch for features: `git checkout -b feat/feature-name`
- Main branch stays runnable at all times

---

## Current Phase
**Phase 2 — Source file wiring and first dev run.**
Goal: `npm run dev` shows the HUD and `python bridge.py` starts without errors.
Audio and AI features come after the window renders correctly.

Update this section as phases complete.
```
Phase 1 ✅ — Repo + dependency scaffold
Phase 2 🔄 — Source files + first render
Phase 3 ⬜ — Audio capture + Whisper integration
Phase 4 ⬜ — GPT-4o suggestions live
Phase 5 ⬜ — Production build + .dmg
```