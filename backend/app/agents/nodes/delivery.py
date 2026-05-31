"""Delivery agent — scores spoken answer on WPM, filler rate, and qualitative delivery."""

from __future__ import annotations

import json
import re

import weave
from langchain_core.messages import HumanMessage, SystemMessage

from app.services.llm import get_llm

_FILLERS = {
    "um", "uh", "like", "you know", "basically", "literally",
    "so", "right", "kind of", "sort of", "actually", "honestly",
}


def _compute_signals(transcript: str, duration_seconds: float) -> tuple[float, float]:
    words = transcript.lower().split()
    word_count = len(words) if words else 1
    minutes = max(duration_seconds / 60, 0.01)
    wpm = round(len(words) / minutes, 1)
    filler_count = sum(1 for w in words if w.strip(".,!?") in _FILLERS)
    filler_rate = round(filler_count / word_count, 3)
    return wpm, filler_rate


@weave.op()
def evaluate_delivery(transcript: str, duration_seconds: float) -> dict:
    """Score spoken delivery: WPM + filler rate computed directly, qualitative score via LLM."""
    wpm, filler_rate = _compute_signals(transcript, duration_seconds)

    llm = get_llm("fast")
    response = llm.invoke([
        SystemMessage(content=(
            "You are a communication coach scoring a spoken interview answer. "
            "Ideal delivery: 120-160 WPM, minimal fillers, clear structure. "
            'Return only valid JSON: {"delivery_score": <float 0-10>, '
            '"structure_notes": "<one sentence>", "clarity_notes": "<one sentence>", '
            '"pacing_notes": "<one sentence>"}'
        )),
        HumanMessage(content=(
            f"Transcript: {transcript}\n"
            f"WPM: {wpm} (ideal 120-160)\n"
            f"Filler rate: {filler_rate:.1%}\n\n"
            "Score delivery on structure, clarity, and pacing."
        )),
    ])

    raw = response.content if isinstance(response.content, str) else str(response.content)
    match = re.search(r"\{[\s\S]*\}", raw)
    parsed = json.loads(match.group()) if match else {}

    return {
        "delivery_score": float(parsed.get("delivery_score", 5.0)),
        "wpm": wpm,
        "filler_rate": filler_rate,
    }
