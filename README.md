# Unlimited AI Voice & Video OS

A separate, open-source-first toolkit for long-script text-to-speech and simple narration-led video assembly.

> This project is isolated in its own repository. It does not modify the YouTube automation repository, any YouTube skill, or any other project.

## Features
- Sentence-aware chunking for long scripts (no fixed application-level character cap).
- Per-chunk retries and a persisted job manifest.
- WAV assembly with FFmpeg; completed chunks are reused when a job is retried.
- FastAPI endpoints for TTS jobs, status, audio download, and image-slideshow video assembly.
- Configurable local HTTP TTS adapter for Kokoro, GPT-SoVITS, or another compatible inference server.
- Docker setup with persistent data volume.

## Reality check on “free and unlimited”
The software is open-source and has no paid API requirement. It does **not** create unlimited free GPU/CPU, storage, network, or cloud hosting. Real generation speed and maximum practical script size depend on your device/server, model, and provider quotas. For a 30–50 minute script, run on a machine with enough RAM/storage and keep `DATA_DIR` on persistent storage.

Voice cloning is intended only for your own voice or a voice you have explicit permission to use. Do not impersonate others or create deceptive audio.

## Run locally
1. Install Python 3.11+ and FFmpeg.
2. Copy `.env.example` to `.env`.
3. Install: `pip install -r requirements.txt`
4. Start: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
5. API docs: `http://localhost:8000/docs`

Default `TTS_PROVIDER=mock` is a pipeline test provider that emits silence, not speech.

## Connect a speech model
Start a local inference HTTP server for Kokoro or GPT-SoVITS, then set:
```env
TTS_PROVIDER=http
TTS_HTTP_URL=http://127.0.0.1:YOUR_PORT/YOUR_WAV_ENDPOINT
TTS_HTTP_TIMEOUT=180
MAX_CHUNK_CHARS=700
CHUNK_RETRIES=3
```
The current adapter sends JSON `{"text":"...","voice":"...","output_format":"wav"}` and expects raw WAV bytes in the response. Model-server APIs differ by version; adapt `app/providers.py` to the exact endpoint and payload. Do not expose an unauthenticated inference server publicly.

## API
- `GET /health`
- `POST /v1/tts` JSON: `{"text":"Long script...","voice":"default","format":"wav"}`
- Optional `Idempotency-Key` header for repeatable job IDs.
- `GET /v1/jobs/{job_id}`
- `GET /v1/jobs/{job_id}/audio`
- `POST /v1/video` multipart: one `audio` file, multiple `images`, optional `seconds_per_image`.

## Docker
`docker compose up --build` (create a local `.env` first). Data persists in `./data`.

## Status
Starter implementation. Before public deployment, add authentication, upload-size limits, rate limiting, job queue/worker supervision, and provider-specific integration tests. GPU model runtimes may require a custom CUDA-enabled image.

MIT licensed. Model weights and third-party services retain their own licenses and terms.
