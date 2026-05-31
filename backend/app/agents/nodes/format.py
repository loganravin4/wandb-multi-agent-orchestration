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
            "Base schema for every question:\n"
            '  {"index": int, "type": "coding"|"behavioral"|"system_design"|"brain_teaser", '
            '"subtype": str, "text": str, "difficulty": "easy"|"medium"|"hard"}\n\n'
            "Choose subtype from these valid values per type:\n"
            "  coding        → algorithms | data_structures | dynamic_programming | debugging | implementation\n"
            "  system_design → distributed_systems | api_design | database_design | scalability | microservices\n"
            "  behavioral    → leadership | conflict_resolution | ownership | collaboration | impact\n"
            "  brain_teaser  → logic_puzzle | estimation | lateral_thinking\n\n"
            "For CODING questions, add these extra fields to the JSON object:\n"
            '  "function_signature": str  — a valid Python def line with typed params and return type\n'
            '     e.g. "def two_sum(nums: list[int], target: int) -> list[int]:"\n'
            '  "examples": [{"input": str, "output": str, "explanation": str}, ...]  — exactly 2 examples\n'
            '     Use concrete values: input = "nums = [2,7,11,15], target = 9", output = "[0,1]"\n'
            '  "constraints": [str, ...]  — 3-5 constraints like "1 <= nums.length <= 10^4"\n\n'
            "DOMAIN CALIBRATION — follow strictly:\n"
            "  Quant/finance/trading/HFT roles: prefer numerical algorithms (Monte Carlo, pricing models, "
            "    statistical arbitrage, order book structures), probability/stats problems, or "
            "    latency-sensitive data structure design. NEVER ask generic HashMap/LinkedList/BFS/DFS "
            "    implementations — these are CS101 and insult the role.\n"
            "  ML/AI/data science roles: prefer model implementation, loss functions, data pipeline "
            "    design, feature engineering logic, or ML system design.\n"
            "  Backend/infrastructure roles: distributed systems, database internals, API design, "
            "    concurrency problems.\n"
            "  Senior/staff/principal: heavy system design and architectural tradeoffs. "
            "    Fewer pure algorithm questions.\n"
            "  Intern/new grad: algorithm problems appropriate to the domain — "
            "    NOT generic CS101 for specialized roles.\n\n"
            "Only include brain_teaser if the company is known for them (quant firms, Google, Jane Street). "
            "A question that could apply to ANY software engineering role is a failure — make it specific. "
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

    return {
        **state,
        "questions": questions,
        "current_index": 0,
        "current_question": current,
        "results": [],
        "phase": "interview",
    }
