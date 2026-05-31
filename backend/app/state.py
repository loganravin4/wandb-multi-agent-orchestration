"""Shared session state types for LangGraph."""

from __future__ import annotations

from typing import Literal, TypedDict


QuestionType = Literal["coding", "behavioral", "system_design", "brain_teaser"]

QuestionSubtype = Literal[
    # coding
    "algorithms", "data_structures", "dynamic_programming", "debugging", "implementation",
    # system_design
    "distributed_systems", "api_design", "database_design", "scalability", "microservices",
    # behavioral
    "leadership", "conflict_resolution", "ownership", "collaboration", "impact",
    # brain_teaser
    "logic_puzzle", "estimation", "lateral_thinking",
]


class Question(TypedDict):
    index: int
    type: QuestionType
    subtype: QuestionSubtype
    text: str
    difficulty: Literal["easy", "medium", "hard"]


class QuestionResult(TypedDict):
    question_index: int
    question_type: QuestionType
    question_subtype: str
    transcript: str
    duration_seconds: float
    content_score: float
    delivery_score: float
    wpm: float
    filler_rate: float
    hint_used: bool
    feedback: str


class SessionState(TypedDict, total=False):
    session_id: str
    job_description: str
    company: str
    role: str
    seniority: str
    interview_format: str
    common_topics: list[str]
    questions: list[Question]
    current_index: int
    results: list[QuestionResult]
    current_question: Question | None
    last_hint: str | None
    report: dict | None
    phase: Literal["ingest", "interview", "report", "done"]
    error: str | None
