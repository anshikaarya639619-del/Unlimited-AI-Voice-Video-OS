from __future__ import annotations
import os, struct, wave
from pathlib import Path
import httpx

class TTSProvider:
    async def synthesize(self, text: str, output: Path, voice: str = "default") -> None:
        raise NotImplementedError

class MockProvider(TTSProvider):
    async def synthesize(self, text: str, output: Path, voice: str = "default") -> None:
        # Valid silent WAV, only for testing the job pipeline.
        output.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output), "wb") as wav:
            wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(22050)
            wav.writeframes(struct.pack("<h", 0) * 2205)

class HTTPProvider(TTSProvider):
    async def synthesize(self, text: str, output: Path, voice: str = "default") -> None:
        url = os.getenv("TTS_HTTP_URL", "").strip()
        if not url: raise RuntimeError("TTS_HTTP_URL is required for TTS_PROVIDER=http")
        timeout = float(os.getenv("TTS_HTTP_TIMEOUT", "180"))
        payload = {"text": text, "voice": voice, "output_format": "wav"}
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "json" in content_type:
                data = response.json()
                raise RuntimeError(f"TTS service returned JSON instead of audio bytes: {str(data)[:500]}")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(response.content)

def get_provider() -> TTSProvider:
    name = os.getenv("TTS_PROVIDER", "mock").lower()
    if name == "mock": return MockProvider()
    if name == "http": return HTTPProvider()
    if name == "kokoro":
        # Kept explicit: Kokoro Python APIs differ by package/version. Use its local
        # HTTP server via HTTPProvider until a pinned runtime is selected.
        raise RuntimeError("For Kokoro, expose a local inference HTTP endpoint and set TTS_PROVIDER=http.")
    raise ValueError(f"Unknown TTS_PROVIDER: {name}")
