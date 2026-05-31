"""Session lifecycle API."""

from __future__ import annotations

import asyncio
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.agents.graph import get_graph
from app.agents.nodes.delivery import evaluate_delivery
from app.agents.nodes.interviewer import evaluate_content, get_socratic_hint
from app.agents.nodes.report import generate_report
from app.observability import init_observability, log_final_metrics, log_turn_metrics
from app.services.transcription import transcribe_audio
from app.state import QuestionResult, SessionState

router = APIRouter(prefix="/sessions", tags=["sessions"])

# In-memory session store
_sessions: dict[str, SessionState] = {}

# Thread pool for running sync agent functions from async endpoints
_executor = ThreadPoolExecutor(max_workers=8)


# ── Request / response models ──────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    job_description: str = Field(..., min_length=10)
    company: str = ""
    role: str = ""
    seniority: str = ""


class CreateSessionResponse(BaseModel):
    session_id: str
    phase: str
    questions: list[dict[str, Any]]


class SessionResponse(BaseModel):
    session_id: str
    phase: str
    current_question: dict[str, Any] | None
    questions: list[dict[str, Any]]
    results: list[dict[str, Any]]
    report: dict[str, Any] | None
    error: str | None


class AnswerRequest(BaseModel):
    transcript: str
    duration_seconds: float = Field(..., gt=0)
    question_index: int = Field(..., ge=0)


class AnswerResponse(BaseModel):
    content_score: float
    delivery_score: float
    wpm: float
    filler_rate: float
    feedback: str
    next_question: dict[str, Any] | None
    session_complete: bool


class HintRequest(BaseModel):
    question_index: int = Field(..., ge=0)
    transcript: str = ""


class HintResponse(BaseModel):
    hint: str


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_session_or_404(session_id: str) -> SessionState:
    state = _sessions.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    return state


async def _run(fn, *args):
    """Run a sync function in the thread pool without blocking the event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, fn, *args)


# ── Endpoints ─────────────────────────────────────────────────────────────────

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
    final = await _run(graph.invoke, initial)
    _sessions[session_id] = final

    return CreateSessionResponse(
        session_id=session_id,
        phase=final.get("phase", "interview"),
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


@router.post("/{session_id}/transcribe")
async def transcribe_session_audio(
    session_id: str,
    audio: UploadFile = File(...),
) -> dict[str, str]:
    _get_session_or_404(session_id)

    suffix = Path(audio.filename).suffix if audio.filename else ".wav"
    content = await audio.read()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        transcript = await _run(transcribe_audio, tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return {"session_id": session_id, "transcript": transcript}


@router.post("/{session_id}/answer", response_model=AnswerResponse)
async def submit_answer(session_id: str, body: AnswerRequest) -> AnswerResponse:
    state = _get_session_or_404(session_id)
    questions = state.get("questions", [])

    if body.question_index >= len(questions):
        raise HTTPException(status_code=400, detail="Invalid question index")

    question = questions[body.question_index]

    # Run content eval and delivery eval in parallel
    content_result, delivery_result = await asyncio.gather(
        _run(evaluate_content, question, body.transcript),
        _run(evaluate_delivery, body.transcript, body.duration_seconds),
    )

    # Build and store QuestionResult
    result: QuestionResult = {
        "question_index": body.question_index,
        "question_type": question["type"],
        "transcript": body.transcript,
        "duration_seconds": body.duration_seconds,
        "content_score": content_result["content_score"],
        "delivery_score": delivery_result["delivery_score"],
        "wpm": delivery_result["wpm"],
        "filler_rate": delivery_result["filler_rate"],
        "hint_used": False,
        "feedback": content_result["feedback"],
    }

    results = list(state.get("results", []))
    results.append(result)

    next_index = body.question_index + 1
    session_complete = next_index >= len(questions)
    next_question = questions[next_index] if not session_complete else None

    _sessions[session_id] = {
        **state,
        "results": results,
        "current_index": next_index,
        "current_question": next_question,
        "phase": "complete" if session_complete else "interview",
    }

    log_turn_metrics(
        question_index=body.question_index,
        question_type=question["type"],
        content_score=content_result["content_score"],
        delivery_score=delivery_result["delivery_score"],
        wpm=delivery_result["wpm"],
        filler_rate=delivery_result["filler_rate"],
        duration_seconds=body.duration_seconds,
    )

    return AnswerResponse(
        content_score=content_result["content_score"],
        delivery_score=delivery_result["delivery_score"],
        wpm=delivery_result["wpm"],
        filler_rate=delivery_result["filler_rate"],
        feedback=content_result["feedback"],
        next_question=next_question,
        session_complete=session_complete,
    )


@router.post("/{session_id}/hint", response_model=HintResponse)
async def get_hint(session_id: str, body: HintRequest) -> HintResponse:
    state = _get_session_or_404(session_id)
    questions = state.get("questions", [])

    if body.question_index >= len(questions):
        raise HTTPException(status_code=400, detail="Invalid question index")

    question = questions[body.question_index]
    hint = await _run(get_socratic_hint, question, body.transcript)

    return HintResponse(hint=hint)


@router.get("/{session_id}/report")
async def get_session_report(session_id: str) -> dict[str, Any]:
    state = _get_session_or_404(session_id)
    results = state.get("results", [])

    if not results:
        raise HTTPException(status_code=400, detail="No answers submitted yet")

    report = await _run(generate_report, results, session_id)

    if report.get("error"):
        raise HTTPException(status_code=500, detail=report["error"])

    log_final_metrics(
        final_content_score=report["avg_content_score"],
        final_delivery_score=report["avg_delivery_score"],
        final_overall=report["avg_overall"],
    )

    _sessions[session_id] = {**state, "report": report, "phase": "done"}

    return report
