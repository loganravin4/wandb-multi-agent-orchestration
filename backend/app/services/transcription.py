"""Local Whisper transcription (CPU)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import whisper

from app.config import get_settings


@lru_cache
def _load_model() -> whisper.Whisper:
    settings = get_settings()
    return whisper.load_model(settings.whisper_model, device=settings.whisper_device)


def transcribe_audio(audio_path: str | Path) -> str:
    """Transcribe an audio file and return the text transcript."""
    model = _load_model()
    result = model.transcribe(str(audio_path), fp16=False)
    return result["text"].strip()
