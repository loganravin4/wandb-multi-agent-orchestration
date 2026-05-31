"""Session lifecycle API."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.agents.graph import get_graph
from app.observability import init_observability
from app.services.transcription import transcribe_audio
from app.state import SessionState

router = APIRouter(prefix="/sessions", tags=["sessions"])

# In-memory store for scaffold; replace with Redis/DB for production
_sessions: dict[str, SessionState] = {}


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
    final = graph.invoke(initial)
    _sessions[session_id] = final

    return CreateSessionResponse(
        session_id=session_id,
        phase=final.get("phase", "interview"),
        questions=final.get("questions", []),
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str) -> SessionResponse:
    state = _sessions.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

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
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    suffix = Path(audio.filename).suffix if audio.filename else ".wav"
    content = await audio.read()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        transcript = transcribe_audio(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    return {"session_id": session_id, "transcript": transcript}
