"""W&B Weave + W&B Core initialization and logging helpers."""

from __future__ import annotations

import os
from typing import Any

import wandb
import weave

from app.state import Question

_initialized = False


def init_observability(session_id: str, job_description: str) -> tuple[Any, Any]:
    """Initialize Weave (LLM tracing) and W&B (session run tracking)."""
    global _initialized

    entity = os.environ.get("WANDB_ENTITY", "")
    project = os.environ.get("WANDB_PROJECT", "loopprep")
    weave_project = f"{entity}/{project}" if entity else project

    weave_client = weave.init(weave_project)
    run = wandb.init(
        project=project,
        name=f"session-{session_id[:8]}",
        config={"session_id": session_id, "job_description_preview": job_description[:500]},
        reinit=True,
    )
    _initialized = True
    return weave_client, run


def log_research_metrics(interview_format: str, common_topics: list[str]) -> None:
    """Log research agent outputs at session start."""
    if wandb.run is not None:
        wandb.log(
            {
                "interview_format": interview_format,
                "common_topics": common_topics,
            },
            step=0,
        )


def log_question_queue_artifact(questions: list[Question], session_id: str) -> None:
    """Version the question queue as a W&B Artifact."""
    if wandb.run is None:
        return

    artifact = wandb.Artifact(
        name=f"question-queue-{session_id[:8]}",
        type="question_queue",
        description="Ordered interview question queue from Format Agent",
    )
    with artifact.new_file("questions.json", mode="w") as f:
        import json

        json.dump(questions, f, indent=2)
    wandb.log_artifact(artifact)


def log_turn_metrics(
    question_index: int,
    question_type: str,
    content_score: float | None = None,
    delivery_score: float | None = None,
    wpm: float | None = None,
    filler_rate: float | None = None,
    hint_used: bool = False,
    duration_seconds: float | None = None,
) -> None:
    """Log per-turn metrics during the interview loop."""
    if wandb.run is None:
        return

    metrics: dict[str, Any] = {
        "question_index": question_index,
        "question_type": question_type,
        "hint_used": int(hint_used),
    }
    if content_score is not None:
        metrics["content_score"] = content_score
    if delivery_score is not None:
        metrics["delivery_score"] = delivery_score
    if wpm is not None:
        metrics["wpm"] = wpm
    if filler_rate is not None:
        metrics["filler_rate"] = filler_rate
    if duration_seconds is not None:
        metrics["duration_seconds"] = duration_seconds

    wandb.log(metrics, step=question_index + 1)


def log_final_metrics(
    final_content_score: float,
    final_delivery_score: float,
    final_overall: float,
) -> None:
    """Close the session run with aggregate scores."""
    if wandb.run is None:
        return

    wandb.log(
        {
            "final_content_score": final_content_score,
            "final_delivery_score": final_delivery_score,
            "final_overall": final_overall,
        }
    )
    wandb.finish()


def publish_question_dataset(questions: list[Question], session_id: str) -> Any:
    """Publish question queue as a Weave Dataset for traceability."""
    rows = [
        {
            "session_id": session_id,
            "index": q["index"],
            "type": q["type"],
            "text": q["text"],
            "difficulty": q["difficulty"],
        }
        for q in questions
    ]
    return weave.Dataset(name=f"question-queue-{session_id[:8]}", rows=rows)
