"""Format agent node — builds the question queue."""

from __future__ import annotations

import json
import re

import weave
from langchain_core.messages import HumanMessage, SystemMessage

from app.observability import log_question_queue_artifact, publish_question_dataset
from app.services.llm import get_llm
from app.state import Question, SessionState


@weave.op()
def format_node(state: SessionState) -> SessionState:
    """Generate a calibrated question queue using JD signals + research context."""
    jd_parsed = state.get("jd_parsed", {})

    llm = get_llm("default")
    response = llm.invoke([
        SystemMessage(content=(
            "Generate exactly 3 mock interview questions as a JSON array. "
            'Each item: {"index": int, "type": "coding"|"behavioral"|"system_design", '
            '"text": str, "difficulty": "easy"|"medium"|"hard"}. '
            "Calibrate question type mix and difficulty to the seniority level and tech stack. "
            "Make the questions specific to the role — reference actual technologies and responsibilities. "
            "Return only valid JSON."
        )),
        HumanMessage(content=(
            f"Role: {state.get('role', '')} at {state.get('company', '')}\n"
            f"Seniority: {state.get('seniority', '') or jd_parsed.get('seniority', 'senior')}\n"
            f"Tech stack: {jd_parsed.get('tech_stack', [])}\n"
            f"Required skills: {jd_parsed.get('required_skills', [])}\n"
            f"Behavioral themes: {jd_parsed.get('behavioral_themes', [])}\n"
            f"Domain focus: {jd_parsed.get('domain_focus', '')}\n"
            f"Interview format: {state.get('interview_format', '')}\n"
            f"Common topics from research: {state.get('common_topics', [])}"
        )),
    ])

    raw = response.content if isinstance(response.content, str) else str(response.content)
    match = re.search(r"\[[\s\S]*\]", raw)
    questions: list[Question] = json.loads(match.group()) if match else []

    session_id = state.get("session_id", "")
    if questions and session_id:
        log_question_queue_artifact(questions, session_id)
        publish_question_dataset(questions, session_id)

    current = questions[0] if questions else None

    # Return only changed keys — LangGraph merges partial updates automatically
    return {
        "questions": questions,
        "current_index": 0,
        "current_question": current,
        "results": [],
        "phase": "interview",
    }
