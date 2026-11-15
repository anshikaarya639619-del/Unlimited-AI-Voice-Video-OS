# Unlimited AI Voice & Video OS

A separate, open-source-first backend for long-script text-to-speech and narration-led video assembly. It is isolated from all other repositories and does not modify YouTube automation or any YouTube skill.

## Real model integrations

### Option A — Kokoro-82M (recommended first setup)
This project connects to the OpenAI-compatible [Kokoro-FastAPI](https://github.com/remsky/Kokoro-FastAPI) server.

CPU server:
```bash
docker run --rm -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-cpu:latest
```
NVIDIA GPU server:
```bash
docker run --rm --gpus all -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-gpu:latest
```
Set in `.env`:
```env
TTS_PROVIDER=kokoro
KOKORO_BASE_URL=http://127.0.0.1:8880
KOKORO_VOICE=af_heart
```
The adapter calls `POST /v1/audio/speech` with `input`, `voice`, `model`, and `response_format=wav`.

### Option B — GPT-SoVITS (reference-voice synthesis)
Run GPT-SoVITS' `api_v2.py` API (default port 9880) on the machine/container where its model and reference audio are available. Configure:
```env
TTS_PROVIDER=gpt-sovits
GPT_SOVITS_BASE_URL=http://127.0.0.1:9880
GPT_SOVITS_REF_AUDIO_PATH=/absolute/path/on/gpt-sovits-server/reference.wav
GPT_SOVITS_PROMPT_TEXT=Exact transcript of the reference audio
GPT_SOVITS_PROMPT_LANG=en
GPT_SOVITS_TEXT_LANG=en
```
The adapter calls `POST /tts` using the documented API v2 JSON fields and expects WAV bytes. The reference audio path must be visible to the GPT-SoVITS server. Use a reference recording you own or have explicit permission to use.

### Provider failover
Set `TTS_PROVIDER=kokoro,gpt-sovits` to try Kokoro first and GPT-SoVITS as a per-chunk fallback. Each provider receives up to `CHUNK_RETRIES` attempts. Completed chunks are saved in the job manifest and skipped on resume.

## Run this API
Requires Python 3.11+, FFmpeg, and a running model server.
```bash
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Docs: `http://localhost:8000/docs`.

## API endpoints
- `GET /health`
- `POST /v1/tts` JSON `{"text":"Long script","voice":"default","format":"wav"}`
- `GET /v1/jobs/{job_id}`
- `GET /v1/jobs/{job_id}/audio`
- `POST /v1/video` multipart form: audio file, multiple images, optional seconds_per_image.

## Long scripts and resource limits
The app has no hard-coded total character cap; it chunks scripts (default 700 characters per chunk), retries failed chunks, and stores progress on disk. “Unlimited” does not mean unlimited free GPU, RAM, storage, network, or hosted inference. Long jobs require persistent storage and a machine capable of running the selected model. Public free hosting may sleep or restrict compute.

## Safety and deployment
Use voice cloning only for your own voice or with explicit permission. Before exposing this API publicly, add authentication, request/upload limits, rate limiting, and background-worker supervision. Do not expose model inference endpoints unauthenticated.

## License
This starter code is MIT licensed. Kokoro, Kokoro-FastAPI, GPT-SoVITS, and their model weights retain their respective licenses and terms.
