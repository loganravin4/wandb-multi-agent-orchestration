"""Delivery agent — scores spoken communication from Whisper transcript."""

from __future__ import annotations

import json
import re

import weave
from langchain_core.messages import HumanMessage, SystemMessage

from app.services.llm import get_llm

_FILLER_WORDS = {"um", "uh", "like", "you know", "basically", "literally", "actually", "so", "right"}

_SYSTEM = """\
You are evaluating the delivery quality of a spoken interview answer.
You receive computed metrics (WPM, filler rate) and the raw transcript.
Return JSON only:

{"delivery_score": float 0-10, "structure_score": float 0-10, "clarity_score": float 0-10, "pacing_comment": "one sentence"}

Scoring guide:
- delivery_score: overall spoken delivery (weighted average of sub-scores)
- structure_score: logical flow, clear beginning/middle/end
- clarity_score: precise language, avoids vague filler, concrete examples
- pacing_comment: brief note on WPM and filler usage

No markdown fences. Valid JSON only."""


def _compute_signals(transcript: str, duration_seconds: float) -> tuple[float, float]:
    """Returns (wpm, filler_rate). filler_rate is fillers-per-minute."""
    words = transcript.split()
    word_count = len(words)
    minutes = max(duration_seconds / 60.0, 0.01)
    wpm = word_count / minutes

    filler_count = sum(
        1 for w in words if w.lower().strip(".,!?") in _FILLER_WORDS
    )
    filler_rate = filler_count / minutes

    return round(wpm, 1), round(filler_rate, 2)


@weave.op()
def eval_delivery(transcript: str, duration_seconds: float) -> dict:
    """Score delivery quality from transcript + duration. Returns scored metrics dict."""
    wpm, filler_rate = _compute_signals(transcript, duration_seconds)

    llm = get_llm("fast")
    response = llm.invoke(
        [
            SystemMessage(content=_SYSTEM),
            HumanMessage(
                content=(
                    f"WPM: {wpm} (target 120-160)\n"
                    f"Filler rate: {filler_rate}/min (target <5)\n"
                    f"Transcript: {transcript[:1200]}"
                )
            ),
        ]
    )

    raw = response.content if isinstance(response.content, str) else str(response.content)
    match = re.search(r"\{[\s\S]*\}", raw)
    result: dict = json.loads(match.group()) if match else {}

    return {
        "delivery_score": float(result.get("delivery_score", 5.0)),
        "structure_score": float(result.get("structure_score", 5.0)),
        "clarity_score": float(result.get("clarity_score", 5.0)),
        "pacing_comment": result.get("pacing_comment", ""),
        "wpm": wpm,
        "filler_rate": filler_rate,
    }
