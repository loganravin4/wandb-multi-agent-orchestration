"""Report agent — generates final session debrief and closes W&B run."""

from __future__ import annotations

import json
import re

import weave
from langchain_core.messages import HumanMessage, SystemMessage

from app.observability import log_final_metrics
from app.services.llm import get_llm
from app.state import QuestionResult

_SYSTEM = """\
You are a senior technical interview coach writing a post-session debrief.
Given per-question scores and feedback, produce a structured debrief as JSON only.

Return exactly:
{
  "summary": "2-3 sentence overall performance summary",
  "strengths": ["specific strength 1", "specific strength 2"],
  "areas_to_improve": ["specific weakness 1", "specific weakness 2"],
  "next_steps": ["concrete action 1", "concrete action 2", "concrete action 3"],
  "final_content_score": float 0-10,
  "final_delivery_score": float 0-10,
  "final_overall": float 0-10
}

No markdown fences. Valid JSON only."""


@weave.op()
def generate_report(results: list[QuestionResult], session_id: str) -> dict:
    """Produce full session debrief and log final W&B metrics."""
    if not results:
        return {
            "summary": "No answers recorded.",
            "strengths": [],
            "areas_to_improve": [],
            "next_steps": [],
            "final_content_score": 0.0,
            "final_delivery_score": 0.0,
            "final_overall": 0.0,
        }

    turns_summary = "\n".join(
        f"Q{r['question_index']+1} ({r['question_type']}): "
        f"content={r['content_score']:.1f}/10, delivery={r['delivery_score']:.1f}/10, "
        f"wpm={r['wpm']:.0f}, filler={r['filler_rate']:.1f}/min, hint={r['hint_used']}\n"
        f"  Feedback: {r.get('feedback', '')}"
        for r in results
    )

    llm = get_llm("synthesis")
    response = llm.invoke(
        [
            SystemMessage(content=_SYSTEM),
            HumanMessage(content=f"Session results:\n{turns_summary}"),
        ]
    )

    raw = response.content if isinstance(response.content, str) else str(response.content)
    match = re.search(r"\{[\s\S]*\}", raw)
    report: dict = json.loads(match.group()) if match else {}

    final_content = float(report.get("final_content_score", 5.0))
    final_delivery = float(report.get("final_delivery_score", 5.0))
    final_overall = float(report.get("final_overall", 5.0))

    log_final_metrics(final_content, final_delivery, final_overall)

    # Publish as weave.Evaluation for the Weave dashboard money shot
    weave.Evaluation(
        name=f"session-{session_id[:8]}",
        dataset=weave.Dataset(
            name=f"results-{session_id[:8]}",
            rows=[dict(r) for r in results],
        ),
    )

    return report
