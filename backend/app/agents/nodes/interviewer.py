"""Interviewer agent — content evaluation and Socratic hint path."""

from __future__ import annotations

import json
import re

import weave
from langchain_core.messages import HumanMessage, SystemMessage

from app.services.llm import get_llm
from app.state import Question

_CONTENT_SYSTEM = (
    "You are a senior interviewer evaluating a candidate's answer. "
    "Scoring rubric by question type:\n"
    "  coding      → correctness, approach, edge cases, time/space complexity\n"
    "  behavioral  → STAR completeness (Situation, Task, Action, Result)\n"
    "  system_design → breadth of components, tradeoffs discussed, clarity\n"
    "Be direct and specific. "
    'Return only valid JSON: {"content_score": <float 0-10>, "feedback": "<2-3 sentences>"}'
)

_HINT_SYSTEM = (
    "You are a Socratic interviewer. The candidate is stuck or asking for help. "
    "Ask exactly ONE guiding question that nudges them toward the answer without revealing it. "
    "Do not state or imply the answer. Return only the guiding question as a plain string."
)


@weave.op()
def evaluate_content(question: Question, transcript: str) -> dict:
    """Score the content of a candidate's answer for the given question type."""
    llm = get_llm("default")
    response = llm.invoke([
        SystemMessage(content=_CONTENT_SYSTEM),
        HumanMessage(content=(
            f"Question type: {question['type']}\n"
            f"Difficulty: {question['difficulty']}\n"
            f"Question: {question['text']}\n\n"
            f"Candidate answer: {transcript}"
        )),
    ])

    raw = response.content if isinstance(response.content, str) else str(response.content)
    match = re.search(r"\{[\s\S]*\}", raw)
    parsed = json.loads(match.group()) if match else {}

    return {
        "content_score": float(parsed.get("content_score", 5.0)),
        "feedback": parsed.get("feedback", ""),
    }


@weave.op()
def get_socratic_hint(question: Question, transcript: str) -> str:
    """Return a Socratic guiding question without revealing the answer."""
    llm = get_llm("default")
    response = llm.invoke([
        SystemMessage(content=_HINT_SYSTEM),
        HumanMessage(content=(
            f"Question: {question['text']}\n"
            f"Candidate said so far: {transcript or '(nothing yet)'}"
        )),
    ])
    return response.content if isinstance(response.content, str) else str(response.content)
