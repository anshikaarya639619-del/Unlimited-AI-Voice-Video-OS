from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .core import split_text, make_job_id, save_json, load_json
from .providers import get_providers

load_dotenv()
DATA = Path(os.getenv("DATA_DIR", "./data")).resolve()
JOBS = DATA / "jobs"
JOBS.mkdir(parents=True, exist_ok=True)
app = FastAPI(title=os.getenv("APP_NAME", "Unlimited AI Voice Video OS"), version="0.2.0")

class TTSRequest(BaseModel):
    text: str = Field(min_length=1)
    voice: str = "default"
    format: str = "wav"

async def run_tts_job(job_id: str, text: str, voice: str) -> None:
    folder = JOBS / job_id
    folder.mkdir(parents=True, exist_ok=True)
    manifest_path = folder / "job.json"
    chunks = split_text(text, int(os.getenv("MAX_CHUNK_CHARS", "700")))
    manifest = load_json(manifest_path) or {
        "job_id": job_id, "status": "queued", "total_chunks": len(chunks),
        "completed": [], "errors": [], "provider_by_chunk": {}
    }
    manifest.update({"status": "running", "total_chunks": len(chunks)})
    save_json(manifest_path, manifest)
    try:
        providers = get_providers()
        retries = max(1, int(os.getenv("CHUNK_RETRIES", "2")))
        for index, chunk in enumerate(chunks):
            target = folder / f"chunk_{index:05d}.wav"
            if index in manifest["completed"] and target.exists():
                continue
            errors = []
            succeeded = False
            for provider in providers:
                for attempt in range(retries):
                    try:
                        await provider.synthesize(chunk, target, voice)
                        if not target.exists() or target.stat().st_size < 44:
                            raise RuntimeError("Provider did not return a valid audio file")
                        manifest["completed"] = sorted(set(manifest["completed"] + [index]))
                        manifest["provider_by_chunk"][str(index)] = provider.name
                        manifest["errors"] = [e for e in manifest["errors"] if e.get("chunk") != index]
                        save_json(manifest_path, manifest)
                        succeeded = True
                        break
                    except Exception as exc:
                        errors.append({"provider": provider.name, "attempt": attempt + 1, "error": str(exc)})
                        await asyncio.sleep(min(2 ** attempt, 8))
                if succeeded:
                    break
            if not succeeded:
                manifest["errors"].append({"chunk": index, "attempts": errors})
                manifest["status"] = "failed"
                save_json(manifest_path, manifest)
                return
        concat_file = folder / "concat.txt"
        concat_file.write_text(
            "".join(f"file '{(folder / f'chunk_{i:05d}.wav').as_posix()}'\n" for i in range(len(chunks))),
            encoding="utf-8"
        )
        output = folder / "speech.wav"
        proc = await asyncio.create_subprocess_exec(
            os.getenv("FFMPEG_BIN", "ffmpeg"), "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_file), "-c", "copy", str(output),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(stderr.decode(errors="ignore")[-1500:])
        manifest.update({"status": "completed", "audio_file": "speech.wav"})
        save_json(manifest_path, manifest)
    except Exception as exc:
        manifest["status"] = "failed"
        manifest["errors"].append({"error": str(exc)})
        save_json(manifest_path, manifest)

@app.get("/health")
async def health():
    return {"ok": True, "service": "voice-video-os", "version": "0.2.0"}

@app.post("/v1/tts", status_code=202)
async def create_tts(req: TTSRequest, idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None):
    if req.format.lower() != "wav":
        raise HTTPException(400, "Currently only WAV output is supported.")
    chunk_limit = int(os.getenv("MAX_CHUNK_CHARS", "700"))
    job_id = make_job_id(req.text, idempotency_key)
    folder = JOBS / job_id
    manifest_path = folder / "job.json"
    existing = load_json(manifest_path)
    if existing and existing.get("status") in ("queued", "running", "completed"):
        return {"job_id": job_id, "status": existing["status"], "reused": True}
    asyncio.create_task(run_tts_job(job_id, req.text, req.voice))
    return {"job_id": job_id, "status": "queued", "chunks": len(split_text(req.text, chunk_limit))}

@app.get("/v1/jobs/{job_id}")
async def get_job(job_id: str):
    manifest = load_json(JOBS / job_id / "job.json")
    if not manifest:
        raise HTTPException(404, "Job not found")
    return manifest

@app.get("/v1/jobs/{job_id}/audio")
async def get_audio(job_id: str):
    path = JOBS / job_id / "speech.wav"
    if not path.exists():
        raise HTTPException(404, "Audio is not ready")
    return FileResponse(path, media_type="audio/wav", filename=f"{job_id}.wav")

@app.post("/v1/video")
async def make_video(audio: UploadFile = File(...), images: list[UploadFile] = File(...), seconds_per_image: float = Form(5.0)):
    if not images:
        raise HTTPException(400, "Upload at least one image")
    if seconds_per_image <= 0 or seconds_per_image > 60:
        raise HTTPException(400, "seconds_per_image must be between 0 and 60")
    job_id = uuid.uuid4().hex[:16]
    folder = DATA / "videos" / job_id
    folder.mkdir(parents=True, exist_ok=True)
    audio_path = folder / "narration"
    audio_path.write_bytes(await audio.read())
    image_paths = []
    for i, item in enumerate(images):
        ext = Path(item.filename or "image.jpg").suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            raise HTTPException(400, "Images must be JPG, PNG or WEBP")
        path = folder / f"image_{i:04d}{ext}"
        path.write_bytes(await item.read())
        image_paths.append(path)
    manifest = folder / "images.txt"
    lines = []
    for path in image_paths:
        lines.extend([f"file '{path.as_posix()}'", f"duration {seconds_per_image}"])
    lines.append(f"file '{image_paths[-1].as_posix()}'")
    manifest.write_text("\n".join(lines), encoding="utf-8")
    output = folder / "video.mp4"
    proc = await asyncio.create_subprocess_exec(
        os.getenv("FFMPEG_BIN", "ffmpeg"), "-y", "-f", "concat", "-safe", "0",
        "-i", str(manifest), "-i", str(audio_path),
        "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
        "-c:v", "libx264", "-r", "30", "-c:a", "aac", "-shortest", str(output),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise HTTPException(500, stderr.decode(errors="ignore")[-1200:])
    return FileResponse(output, media_type="video/mp4", filename=f"{job_id}.mp4")
