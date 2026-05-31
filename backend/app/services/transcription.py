from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from faster_whisper import WhisperModel

from app.config import get_settings


@lru_cache
def _load_model() -> WhisperModel:
    settings = get_settings()
    return WhisperModel(
        settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )


def transcribe_audio(audio_path: str | Path) -> str:
    model = _load_model()
    segments, _ = model.transcribe(str(audio_path))
    return " ".join(segment.text for segment in segments).strip()
