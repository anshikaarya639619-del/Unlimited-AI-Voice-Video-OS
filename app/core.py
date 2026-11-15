from __future__ import annotations
import hashlib, json, re, uuid
from pathlib import Path
from typing import Iterable

def split_text(text: str, limit: int = 700) -> list[str]:
    """Split on sentence boundaries where possible; never emit an empty chunk."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    if limit < 80:
        raise ValueError("chunk limit must be at least 80 characters")
    sentences = re.split(r"(?<=[.!?।])\s+", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        while len(sentence) > limit:
            if current:
                chunks.append(current); current = ""
            cut = sentence.rfind(" ", 0, limit + 1)
            if cut < limit // 2:
                cut = limit
            chunks.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        candidate = f"{current} {sentence}".strip()
        if len(candidate) <= limit:
            current = candidate
        else:
            if current: chunks.append(current)
            current = sentence
    if current: chunks.append(current)
    return [c for c in chunks if c]

def make_job_id(text: str, key: str | None = None) -> str:
    seed = key or f"{uuid.uuid4()}:{text}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]

def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

def load_json(path: Path) -> dict | None:
    if not path.exists(): return None
    return json.loads(path.read_text(encoding="utf-8"))
