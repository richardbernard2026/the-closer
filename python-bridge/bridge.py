import asyncio
import json
import os
import tempfile
import wave
from pathlib import Path

from dotenv import load_dotenv
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
import sounddevice as sd
import openai

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    print('[warn] OPENAI_API_KEY is not set. AI features disabled until key is added to python-bridge/.env', flush=True)

client = openai.OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

SAMPLE_RATE = 16000
CHUNK_SECONDS = 5
CHUNK_SAMPLES = SAMPLE_RATE * CHUNK_SECONDS

SYSTEM_PROMPT = (
    'You are an expert interview coach listening to a live conversation. '
    'Given the transcript snippet, output 1-3 short coaching phrases (3-5 words each) '
    'that the interviewer could use next. Focus on: probing deeper, active listening, '
    'or transitioning topics. Respond with raw JSON only: '
    '{"bullets": ["phrase 1", "phrase 2"]}'
)

app = FastAPI()

capturing = False
audio_buffer: list[float] = []
connected_clients: list[WebSocket] = []


async def broadcast(msg: dict):
    data = json.dumps(msg)
    for ws in list(connected_clients):
        try:
            await ws.send_text(data)
        except Exception:
            pass


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

    if not client:
        return

    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        tmp_path = f.name

    try:
        with wave.open(tmp_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
            wf.writeframes(pcm.tobytes())

        loop = asyncio.get_event_loop()

        with open(tmp_path, 'rb') as f:
            transcript_text = await loop.run_in_executor(
                None,
                lambda: client.audio.transcriptions.create(
                    model='whisper-1',
                    file=f,
                    response_format='text',
                ),
            )

        text = str(transcript_text).strip()
        if not text:
            return

        await broadcast({'type': 'transcript', 'text': text})

        suggestion_resp = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model='gpt-4o',
                messages=[
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                    {'role': 'user', 'content': text},
                ],
                temperature=0.4,
                max_tokens=120,
                response_format={'type': 'json_object'},
            ),
        )

        raw = suggestion_resp.choices[0].message.content
        data = json.loads(raw)
        bullets = data.get('bullets', [])[:3]
        if bullets:
            await broadcast({'type': 'suggestion', 'bullets': bullets})

    except Exception as e:
        print(f'[error] Chunk processing failed: {e}', flush=True)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


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
