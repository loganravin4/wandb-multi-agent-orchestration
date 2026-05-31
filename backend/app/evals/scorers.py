"""Scorers for the Format agent evaluation.

Two deterministic scorers (no API) plus one LLM-as-judge scorer that runs on
W&B Serverless Inference. All are @weave.op so they appear in the trace tree.
"""

from __future__ import annotations

import json
import re

import weave

from app.config import get_settings
from app.services.llm import complete
from app.state import Question

VALID_TYPES = {"coding", "behavioral", "system_design"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}


@weave.op()
def question_count_ok(questions: list[Question]) -> float:
    """1.0 if the agent produced exactly 3 questions, else 0.0."""
    return 1.0 if len(questions) == 3 else 0.0


@weave.op()
def schema_validity(questions: list[Question]) -> float:
    """Fraction of questions with a valid type, difficulty, and non-empty text."""
    if not questions:
        return 0.0
    valid = sum(
        1
        for q in questions
        if isinstance(q, dict)
        and q.get("type") in VALID_TYPES
        and q.get("difficulty") in VALID_DIFFICULTIES
        and str(q.get("text", "")).strip()
    )
    return valid / len(questions)


@weave.op()
def relevance_judge(job_description: str, questions: list[Question]) -> float:
    """LLM-as-judge: how relevant are the questions to the JD (0.0–1.0)."""
    if not questions:
        return 0.0

    listed = "\n".join(f"{i + 1}. {q.get('text', '')}" for i, q in enumerate(questions))
    raw = complete(
        [
            {
                "role": "system",
                "content": (
                    "You grade how well a set of mock-interview questions matches a "
                    "job description. Reply with ONLY a JSON object: "
                    '{"score": <float 0..1>} where 1.0 means highly relevant and '
                    "well-targeted, 0.0 means irrelevant."
                ),
            },
            {
                "role": "user",
                "content": f"Job description:\n{job_description}\n\nQuestions:\n{listed}",
            },
        ],
        model=get_settings().model_judge,
        temperature=0.0,
    )

    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        return 0.0
    try:
        score = float(json.loads(match.group()).get("score", 0.0))
    except (ValueError, json.JSONDecodeError):
        return 0.0
    return max(0.0, min(1.0, score))
