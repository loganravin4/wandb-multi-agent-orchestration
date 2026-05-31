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


def transcribe_audio(audio_path: str | Path) -> tuple[str, float]:
    """Returns (transcript, duration_seconds)."""
    model = _load_model()
    segments, info = model.transcribe(str(audio_path))
    transcript = " ".join(segment.text for segment in segments).strip()
    return transcript, info.duration
