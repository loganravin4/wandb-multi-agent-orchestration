from __future__ import annotations

from pathlib import Path

import weave

from app.config import get_settings


@weave.op()
def transcribe_audio(audio_path: str | Path) -> str:
    from groq import Groq

    settings = get_settings()
    client = Groq(api_key=settings.groq_api_key)

    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=(Path(audio_path).name, f),
            model="whisper-large-v3-turbo",
        )

    return transcription.text.strip()
