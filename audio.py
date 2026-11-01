"""Speech-to-text for audio uploads.

Uses faster-whisper on your machine when it is installed. Cloud transcription (OpenAI) is only
used when the caller allows it, because it sends the audio off the machine.
"""
import os
import tempfile
from pathlib import Path

import httpx
from fastapi import HTTPException

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
OPENAI_TRANSCRIBE_URL = os.getenv("OPENAI_TRANSCRIBE_URL", "https://api.openai.com/v1/audio/transcriptions")
OPENAI_TRANSCRIBE_MODEL = os.getenv("OPENAI_TRANSCRIBE_MODEL", "whisper-1")

_model = None


def _load_local():
    """Return a faster-whisper model, or None if the package isn't installed."""
    global _model
    if _model is None:
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            return None
        _model = WhisperModel(WHISPER_MODEL, compute_type="int8")
    return _model


def transcribe(name: str, mime: str, data: bytes, allow_cloud: bool) -> str:
    model = _load_local()
    if model is not None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / f"audio{Path(name).suffix or '.wav'}"
            path.write_bytes(data)
            segments, _ = model.transcribe(str(path))
            return " ".join(s.text.strip() for s in segments)

    key = os.getenv("OPENAI_API_KEY")
    if key and allow_cloud:
        try:
            r = httpx.post(
                OPENAI_TRANSCRIBE_URL,
                headers={"Authorization": f"Bearer {key}"},
                files={"file": (name, data, mime or "application/octet-stream")},
                data={"model": OPENAI_TRANSCRIBE_MODEL},
                timeout=300,
            )
        except httpx.HTTPError as e:
            raise HTTPException(502, f"Can't reach OpenAI for transcription: {e}") from None
        if r.status_code != 200:
            raise HTTPException(502, f"OpenAI transcription error: {r.text[:300]}")
        return str(r.json().get("text", ""))

    raise HTTPException(
        501,
        "Audio needs speech-to-text. Install it on this machine with `pip install faster-whisper`, "
        "or choose ChatGPT (with OPENAI_API_KEY set) to transcribe in the cloud.",
    )
