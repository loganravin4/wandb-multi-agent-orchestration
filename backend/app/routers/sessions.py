"""Session lifecycle API."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.agents.graph import get_graph
from app.agents.nodes.delivery import eval_delivery
from app.agents.nodes.interviewer import eval_content, get_hint
from app.agents.nodes.report import generate_report
from app.observability import init_observability, log_turn_metrics
from app.services.transcription import transcribe_audio
from app.state import QuestionResult, SessionState

router = APIRouter(prefix="/sessions", tags=["sessions"])

# In-memory store — fine for the hackathon, swap for Redis/DB later
_sessions: dict[str, SessionState] = {}


# ── Request / Response models ─────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    job_description: str = Field(..., min_length=10)
    company: str = ""
    role: str = ""
    seniority: str = ""


class CreateSessionResponse(BaseModel):
    session_id: str
    phase: str
    current_question: dict[str, Any] | None
    questions: list[dict[str, Any]]


class SessionResponse(BaseModel):
    session_id: str
    phase: str
    current_question: dict[str, Any] | None
    questions: list[dict[str, Any]]
    results: list[dict[str, Any]]
    report: dict[str, Any] | None
    error: str | None


class TranscribeResponse(BaseModel):
    session_id: str
    transcript: str
    duration_seconds: float
    content_score: float
    delivery_score: float
    wpm: float
    filler_rate: float
    feedback: str
    hint_used: bool
    next_question: dict[str, Any] | None
    phase: str


class HintResponse(BaseModel):
    session_id: str
    hint: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_session_or_404(session_id: str) -> SessionState:
    state = _sessions.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return state


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("", response_model=CreateSessionResponse)
async def create_session(body: CreateSessionRequest) -> CreateSessionResponse:
    session_id = str(uuid.uuid4())
    initial: SessionState = {
        "session_id": session_id,
        "job_description": body.job_description,
        "company": body.company,
        "role": body.role,
        "seniority": body.seniority,
        "phase": "ingest",
        "results": [],
    }

    init_observability(session_id, body.job_description)

    graph = get_graph()
    final: SessionState = graph.invoke(initial)
    _sessions[session_id] = final

    return CreateSessionResponse(
        session_id=session_id,
        phase=final.get("phase", "interview"),
        current_question=final.get("current_question"),
        questions=final.get("questions", []),
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str) -> SessionResponse:
    state = _get_session_or_404(session_id)
    return SessionResponse(
        session_id=session_id,
        phase=state.get("phase", "ingest"),
        current_question=state.get("current_question"),
        questions=state.get("questions", []),
        results=state.get("results", []),
        report=state.get("report"),
        error=state.get("error"),
    )


@router.post("/{session_id}/transcribe", response_model=TranscribeResponse)
async def transcribe_and_eval(
    session_id: str,
    audio: UploadFile = File(...),
) -> TranscribeResponse:
    state = _get_session_or_404(session_id)

    if state.get("phase") != "interview":
        raise HTTPException(status_code=409, detail=f"Session is in phase '{state.get('phase')}', not 'interview'")

    current_question = state.get("current_question")
    if not current_question:
        raise HTTPException(status_code=409, detail="No active question — session may already be complete")

    # Write audio to temp file and transcribe
    suffix = Path(audio.filename).suffix if audio.filename else ".wav"
    content = await audio.read()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        transcript, duration_seconds = transcribe_audio(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    # Run content eval and delivery eval (sequentially — W&B rate limit safe)
    content_result = eval_content(current_question, transcript)
    delivery_result = eval_delivery(transcript, duration_seconds)

    hint_used = bool(state.get("last_hint"))

    result: QuestionResult = {
        "question_index": current_question["index"],
        "question_type": current_question["type"],
        "transcript": transcript,
        "duration_seconds": duration_seconds,
        "content_score": content_result["content_score"],
        "delivery_score": delivery_result["delivery_score"],
        "wpm": delivery_result["wpm"],
        "filler_rate": delivery_result["filler_rate"],
        "hint_used": hint_used,
        "feedback": content_result["feedback"],
    }

    log_turn_metrics(
        question_index=current_question["index"],
        question_type=current_question["type"],
        content_score=content_result["content_score"],
        delivery_score=delivery_result["delivery_score"],
        wpm=delivery_result["wpm"],
        filler_rate=delivery_result["filler_rate"],
        hint_used=hint_used,
        duration_seconds=duration_seconds,
    )

    # Advance state
    results = list(state.get("results", [])) + [result]
    questions = state.get("questions", [])
    next_index = current_question["index"] + 1
    next_question = questions[next_index] if next_index < len(questions) else None
    phase = "interview" if next_question else "complete"

    _sessions[session_id] = {
        **state,
        "results": results,
        "current_index": next_index,
        "current_question": next_question,
        "last_hint": None,
        "phase": phase,
    }

    return TranscribeResponse(
        session_id=session_id,
        transcript=transcript,
        duration_seconds=duration_seconds,
        content_score=content_result["content_score"],
        delivery_score=delivery_result["delivery_score"],
        wpm=delivery_result["wpm"],
        filler_rate=delivery_result["filler_rate"],
        feedback=content_result["feedback"],
        hint_used=hint_used,
        next_question=next_question,
        phase=phase,
    )


@router.post("/{session_id}/hint", response_model=HintResponse)
async def request_hint(session_id: str) -> HintResponse:
    state = _get_session_or_404(session_id)

    if state.get("phase") != "interview":
        raise HTTPException(status_code=409, detail=f"Session is in phase '{state.get('phase')}', not 'interview'")

    current_question = state.get("current_question")
    if not current_question:
        raise HTTPException(status_code=409, detail="No active question")

    hint = get_hint(current_question)
    _sessions[session_id] = {**state, "last_hint": hint}

    return HintResponse(session_id=session_id, hint=hint)


@router.get("/{session_id}/report")
async def get_report(session_id: str) -> dict[str, Any]:
    state = _get_session_or_404(session_id)

    if state.get("phase") not in ("complete", "done"):
        raise HTTPException(
            status_code=409,
            detail=f"Session is in phase '{state.get('phase')}' — complete all questions before fetching the report",
        )

    # Return cached report if already generated
    if state.get("report"):
        return {"session_id": session_id, **state["report"]}

    report = generate_report(state.get("results", []), session_id)
    _sessions[session_id] = {**state, "report": report, "phase": "done"}

    return {"session_id": session_id, **report}
