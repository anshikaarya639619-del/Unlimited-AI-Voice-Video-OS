from __future__ import annotations

import os
import struct
import wave
from pathlib import Path
import httpx

class ProviderError(RuntimeError):
    pass

class TTSProvider:
    name = "base"
    async def synthesize(self, text: str, output: Path, voice: str = "default") -> None:
        raise NotImplementedError

class MockProvider(TTSProvider):
    """Pipeline-test provider. Writes silence; it is not speech synthesis."""
    name = "mock"
    async def synthesize(self, text: str, output: Path, voice: str = "default") -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(22050)
            wav.writeframes(struct.pack("<h", 0) * 2205)

class KokoroProvider(TTSProvider):
    """Kokoro-FastAPI / OpenAI-compatible /v1/audio/speech adapter."""
    name = "kokoro"
    async def synthesize(self, text: str, output: Path, voice: str = "default") -> None:
        base = os.getenv("KOKORO_BASE_URL", "http://127.0.0.1:8880").rstrip("/")
        url = base if base.endswith("/v1/audio/speech") else base + "/v1/audio/speech"
        payload = {
            "model": os.getenv("KOKORO_MODEL", "kokoro"),
            "voice": voice if voice != "default" else os.getenv("KOKORO_VOICE", "af_heart"),
            "input": text,
            "response_format": "wav",
            "speed": float(os.getenv("TTS_SPEED", "1.0")),
        }
        await _post_audio(url, payload, output, float(os.getenv("TTS_HTTP_TIMEOUT", "300")))

class GPTSoVITSProvider(TTSProvider):
    """GPT-SoVITS api_v2.py /tts adapter. Reference audio path is on model server."""
    name = "gpt-sovits"
    async def synthesize(self, text: str, output: Path, voice: str = "default") -> None:
        base = os.getenv("GPT_SOVITS_BASE_URL", "http://127.0.0.1:9880").rstrip("/")
        url = base if base.endswith("/tts") else base + "/tts"
        ref_audio = os.getenv("GPT_SOVITS_REF_AUDIO_PATH", "").strip()
        prompt_text = os.getenv("GPT_SOVITS_PROMPT_TEXT", "").strip()
        if not ref_audio:
            raise ProviderError("Set GPT_SOVITS_REF_AUDIO_PATH to a reference audio path visible to the GPT-SoVITS server.")
        if not prompt_text:
            raise ProviderError("Set GPT_SOVITS_PROMPT_TEXT to the exact transcript of the reference audio.")
        payload = {
            "text": text,
            "text_lang": os.getenv("GPT_SOVITS_TEXT_LANG", "en").strip(),
            "ref_audio_path": ref_audio,
            "prompt_text": prompt_text,
            "prompt_lang": os.getenv("GPT_SOVITS_PROMPT_LANG", "en").strip(),
            "text_split_method": "cut5",
            "batch_size": int(os.getenv("GPT_SOVITS_BATCH_SIZE", "1")),
            "media_type": "wav",
            "streaming_mode": False,
            "speed_factor": float(os.getenv("TTS_SPEED", "1.0")),
        }
        await _post_audio(url, payload, output, float(os.getenv("TTS_HTTP_TIMEOUT", "600")))

class GenericHTTPProvider(TTSProvider):
    name = "http"
    async def synthesize(self, text: str, output: Path, voice: str = "default") -> None:
        url = os.getenv("TTS_HTTP_URL", "").strip()
        if not url:
            raise ProviderError("TTS_HTTP_URL is required when TTS_PROVIDER=http.")
        await _post_audio(url, {"text": text, "voice": voice, "output_format": "wav"},
                          output, float(os.getenv("TTS_HTTP_TIMEOUT", "300")))

async def _post_audio(url: str, payload: dict, output: Path, timeout: float) -> None:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload)
        if response.status_code >= 400:
            raise ProviderError(f"TTS HTTP {response.status_code}: {response.text[:800]}")
        content_type = response.headers.get("content-type", "").lower()
        if "json" in content_type:
            raise ProviderError(f"TTS server returned JSON instead of audio: {response.text[:800]}")
        data = response.content
        if len(data) < 44 or not (data[:4] == b"RIFF" or content_type.startswith("audio/")):
            raise ProviderError("TTS response does not look like a WAV/audio file.")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)

def get_providers() -> list[TTSProvider]:
    """Comma-separated provider order; each chunk falls back to the next provider."""
    names = [x.strip().lower() for x in os.getenv("TTS_PROVIDER", "mock").split(",") if x.strip()]
    if not names:
        raise ProviderError("TTS_PROVIDER is empty.")
    if "mock" in names:
        if names != ["mock"]:
            raise ProviderError("Mock is a test-only provider and cannot be combined with real providers.")
        return [MockProvider()]
    result: list[TTSProvider] = []
    for name in names:
        if name == "kokoro":
            result.append(KokoroProvider())
        elif name in ("gpt-sovits", "gpt_sovits"):
            result.append(GPTSoVITSProvider())
        elif name == "http":
            result.append(GenericHTTPProvider())
        else:
            raise ProviderError(f"Unknown TTS provider: {name}")
    return result

def get_provider() -> TTSProvider:
    providers = get_providers()
    if len(providers) != 1:
        raise ProviderError("Multiple providers configured; use get_providers().")
    return providers[0]
