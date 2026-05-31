"""Interviewer agent — content evaluation and Socratic hint generation."""

from __future__ import annotations

import json
import re

import weave
from langchain_core.messages import HumanMessage, SystemMessage

from app.services.llm import get_llm
from app.state import Question

_EVAL_SYSTEM = """\
You are a technical interviewer evaluating a candidate's answer. Score the answer and return JSON only.

For coding questions evaluate: correctness, approach, edge cases.
For behavioral questions evaluate: STAR completeness, specificity, impact.
For system design questions evaluate: scalability, trade-offs, clarity.

Return exactly:
{"content_score": float 0-10, "feedback": "2-3 sentence specific feedback"}

No markdown fences. Valid JSON only."""

_HINT_SYSTEM = """\
You are a Socratic interview coach. The candidate asked for a hint.
Ask ONE guiding question that nudges them toward the answer without revealing it.
Be concise. Return only the guiding question."""


@weave.op()
def eval_content(question: Question, transcript: str) -> dict:
    """Score candidate answer for content quality. Returns {content_score, feedback}."""
    llm = get_llm("default")
    response = llm.invoke(
        [
            SystemMessage(content=_EVAL_SYSTEM),
            HumanMessage(
                content=(
                    f"Question ({question['type']}, {question['difficulty']}): {question['text']}\n\n"
                    f"Candidate answer: {transcript}"
                )
            ),
        ]
    )

    raw = response.content if isinstance(response.content, str) else str(response.content)
    match = re.search(r"\{[\s\S]*\}", raw)
    result: dict = json.loads(match.group()) if match else {}

    return {
        "content_score": float(result.get("content_score", 5.0)),
        "feedback": result.get("feedback", ""),
    }


@weave.op()
def get_hint(question: Question) -> str:
    """Generate a Socratic guiding question for the candidate."""
    llm = get_llm("default")
    response = llm.invoke(
        [
            SystemMessage(content=_HINT_SYSTEM),
            HumanMessage(content=f"Interview question: {question['text']}"),
        ]
    )
    return response.content if isinstance(response.content, str) else str(response.content)
