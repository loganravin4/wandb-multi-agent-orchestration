"""Interviewer agent — content evaluation and Socratic hint path."""

from __future__ import annotations

import json
import re

import weave
from langchain_core.messages import HumanMessage, SystemMessage

from app.services.llm import get_llm
from app.state import Question

_CONTENT_SYSTEM = (
    "You are a strict senior interviewer evaluating a candidate's spoken answer. "
    "Score ONLY what was actually said — no benefit of the doubt.\n\n"
    "SCORE ANCHORS — calibrate every score against these:\n"
    "  0-1 → Non-answer: gibberish, insults, refusal, off-topic, or fewer than 2 relevant words\n"
    "  2-3 → Attempted but fundamentally wrong or missing 80%+ of required content\n"
    "  4-5 → Correct direction but major gaps — key points absent or poorly explained\n"
    "  6-7 → Solid answer covering most key points with minor gaps\n"
    "  8-9 → Strong, complete answer with good depth and specificity\n"
    "  10  → Exceptional — precise, handles edge cases, demonstrates clear mastery\n\n"
    "Rubric by question type:\n"
    "  behavioral    → STAR completeness (Situation, Task, Action, Result)\n"
    "  system_design → components identified, tradeoffs explicitly discussed, clarity\n"
    "  brain_teaser  → logical reasoning, structured thought process, arrives at correct conclusion\n"
    "The subtype narrows emphasis. "
    "A non-answer MUST score 0-1 regardless of question type — do not inflate. "
    "Feedback MUST open with the score and single biggest reason "
    "(e.g. '1/10 — the response contained no relevant content.'). "
    "Then one strength (or 'none' if score < 3) and one concrete fix. "
    'Return only valid JSON: {"content_score": <float 0-10>, "feedback": "<2-3 sentences>"}'
)

_CODE_EVAL_SYSTEM = (
    "You are a senior software engineer conducting a technical interview code review. "
    "You will receive the problem statement, function signature, expected examples, and the candidate's Python code with its actual run output.\n\n"
    "Score the submission on these dimensions (weighted equally):\n"
    "  1. Correctness   — does the output match expected outputs for the given examples?\n"
    "  2. Approach      — is the algorithm sound? Is the time/space complexity appropriate?\n"
    "  3. Code quality  — readable variable names, clean structure, no unnecessary complexity\n"
    "  4. Edge cases    — does the code handle boundaries, empty inputs, duplicates, etc.?\n\n"
    "Score bands: runtime error or wrong output → 1-4 | right approach with bug → 5-6 | correct but suboptimal → 7-8 | correct and optimal → 9-10.\n\n"
    "Your feedback MUST open by stating the score and the primary reason for it "
    "(e.g. '4/10 — the output is incorrect: got [1,0] but expected [0,1] for example 1.'). "
    "Then name one thing done well and one concrete fix. Reference specific line numbers or variable names when relevant. "
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
    # Short-circuit non-answers before spending an LLM call
    words = [w for w in transcript.strip().split() if any(c.isalpha() for c in w)]
    if len(words) < 4:
        return {
            "content_score": 0.5,
            "feedback": "0.5/10 — No meaningful answer was provided. Attempt the question fully before submitting.",
        }

    llm = get_llm("default")

    if question["type"] == "coding":
        examples = question.get("examples", [])
        examples_text = "\n".join(
            f"  Example {i+1}: input={ex['input']} → output={ex['output']}"
            + (f" ({ex['explanation']})" if ex.get("explanation") else "")
            for i, ex in enumerate(examples)
        )
        constraints = question.get("constraints", [])
        human_content = (
            f"Problem: {question['text']}\n"
            f"Function signature: {question.get('function_signature', '(not provided)')}\n"
            f"Difficulty: {question['difficulty']} / {question.get('subtype', '')}\n"
        )
        if examples_text:
            human_content += f"Expected examples:\n{examples_text}\n"
        if constraints:
            human_content += f"Constraints: {', '.join(constraints)}\n"
        human_content += f"\nCandidate's code and output:\n{transcript}"

        system = _CODE_EVAL_SYSTEM
    else:
        human_content = (
            f"Question type: {question['type']} / {question.get('subtype', '')}\n"
            f"Difficulty: {question['difficulty']}\n"
            f"Question: {question['text']}\n\n"
            f"Candidate answer: {transcript}"
        )
        system = _CONTENT_SYSTEM

    response = llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=human_content),
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
