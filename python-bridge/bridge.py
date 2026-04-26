import asyncio
import io
import json
import os
import wave
from collections import deque

from dotenv import load_dotenv
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
import sounddevice as sd
import groq

load_dotenv()

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
ai_enabled = bool(GROQ_API_KEY)
if not ai_enabled:
    print('[warn] GROQ_API_KEY is not set. AI features disabled until key is added to python-bridge/.env', flush=True)

client = groq.Groq(api_key=GROQ_API_KEY) if ai_enabled else None

SAMPLE_RATE = 16000
CHUNK_SECONDS = 3
CHUNK_SAMPLES = SAMPLE_RATE * CHUNK_SECONDS

SYSTEM_PROMPT = (
    'You are a real-time interview coach. Given this transcript snippet, '
    'reply with exactly 3 short trigger phrases (5 words max each) the speaker '
    'should say next. Return only a JSON array of 3 strings. No explanation.'
)

app = FastAPI()

capturing = False
audio_buffer: list[float] = []
connected_clients: list[WebSocket] = []
transcript_buffer: deque[str] = deque(maxlen=20)  # 20 × 3s ≈ 60s rolling window


async def broadcast(msg: dict):
    data = json.dumps(msg)
    for ws in list(connected_clients):
        try:
            await ws.send_text(data)
        except Exception:
            pass


async def broadcast_bytes(data: bytes):
    for ws in list(connected_clients):
        try:
            await ws.send_bytes(data)
        except Exception:
            pass


def encode_wav(samples: 'np.ndarray') -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


def find_loopback_device():
    for i, dev in enumerate(sd.query_devices()):
        name = dev['name'].lower()
        if dev['max_input_channels'] > 0 and any(
            k in name for k in ('loopback', 'stereo mix', 'soundflower', 'blackhole')
        ):
            return i, dev['name']
    default = sd.default.device[0]
    name = sd.query_devices(default)['name']
    print(f'[warn] No loopback device found. Falling back to default mic: {name}', flush=True)
    return default, name


async def process_chunk(chunk: list[float]):
    samples = np.array(chunk, dtype=np.float32)

    rms = float(np.sqrt(np.mean(samples ** 2)))
    await broadcast({'type': 'audio-level', 'level': min(rms * 5, 1.0)})
    wav_bytes = encode_wav(samples)
    await broadcast_bytes(wav_bytes)

    if not client:
        return

    loop = asyncio.get_event_loop()

    try:
        transcript_resp = await loop.run_in_executor(
            None,
            lambda: client.audio.transcriptions.create(
                model='whisper-large-v3',
                file=('audio.wav', wav_bytes),
            ),
        )

        text = transcript_resp.text.strip()
        if not text:
            return

        transcript_buffer.append(text)
        await broadcast({'type': 'transcript', 'text': text})

        rolling_text = ' '.join(transcript_buffer)
        suggestion_resp = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model='llama-3.1-8b-instant',
                messages=[
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                    {'role': 'user', 'content': rolling_text},
                ],
                temperature=0.4,
                max_tokens=120,
            ),
        )

        raw = suggestion_resp.choices[0].message.content.strip()
        items = json.loads(raw)
        if isinstance(items, list) and items:
            await broadcast({'type': 'suggestions', 'items': items[:3]})

    except Exception as e:
        print(f'[error] Chunk processing failed: {e}', flush=True)


@app.websocket('/')
async def websocket_endpoint(websocket: WebSocket):
    global capturing, audio_buffer

    await websocket.accept()
    connected_clients.append(websocket)
    print(f'[ws] Client connected. Total: {len(connected_clients)}', flush=True)

    loop = asyncio.get_event_loop()
    device_idx, device_name = find_loopback_device()
    stream = None

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            command = msg.get('command')

            if command == 'start' and not capturing:
                capturing = True
                audio_buffer = []

                def audio_callback(indata, frames, time_info, status):
                    if not capturing:
                        return
                    mono = indata[:, 0].tolist()
                    audio_buffer.extend(mono)
                    if len(audio_buffer) >= CHUNK_SAMPLES:
                        chunk = audio_buffer[:CHUNK_SAMPLES]
                        audio_buffer[:] = audio_buffer[CHUNK_SAMPLES:]
                        asyncio.run_coroutine_threadsafe(process_chunk(chunk), loop)

                stream = sd.InputStream(
                    device=device_idx,
                    samplerate=SAMPLE_RATE,
                    channels=1,
                    dtype='float32',
                    blocksize=1024,
                    callback=audio_callback,
                )
                stream.start()
                print(f'[audio] Capturing from: {device_name}', flush=True)
                await broadcast({'type': 'status', 'capturing': True})

            elif command == 'stop' and capturing:
                capturing = False
                if stream:
                    stream.stop()
                    stream.close()
                    stream = None
                audio_buffer = []
                await broadcast({'type': 'status', 'capturing': False})

    except (WebSocketDisconnect, Exception):
        pass
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        if stream:
            stream.stop()
            stream.close()
        if not connected_clients:
            capturing = False
        print(f'[ws] Client disconnected. Remaining: {len(connected_clients)}', flush=True)


if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8765, log_level='info')
