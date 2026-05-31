"""Format agent node — builds the question queue."""

from __future__ import annotations

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.observability import log_question_queue_artifact, publish_question_dataset
from app.services.llm import get_llm
from app.state import Question, SessionState


def format_node(state: SessionState) -> SessionState:
    """Generate an ordered question queue from research context."""
    llm = get_llm("default")
    response = llm.invoke(
        [
            SystemMessage(
                content=(
                    "Generate exactly 3 mock interview questions as JSON array. "
                    'Each item: {"index": int, "type": "coding"|"behavioral"|"system_design", '
                    '"text": str, "difficulty": "easy"|"medium"|"hard"}. '
                    "Return only valid JSON."
                )
            ),
            HumanMessage(
                content=(
                    f"Format: {state.get('interview_format', '')}\n"
                    f"Topics: {state.get('common_topics', [])}\n"
                    f"Role: {state.get('role', '')} at {state.get('company', '')}"
                )
            ),
        ]
    )

    raw = response.content if isinstance(response.content, str) else str(response.content)
    match = re.search(r"\[[\s\S]*\]", raw)
    questions: list[Question] = json.loads(match.group()) if match else []

    session_id = state.get("session_id", "")
    if questions and session_id:
        log_question_queue_artifact(questions, session_id)
        publish_question_dataset(questions, session_id)

    current = questions[0] if questions else None

    return {
        **state,
        "questions": questions,
        "current_index": 0,
        "current_question": current,
        "results": [],
        "phase": "interview",
    }
