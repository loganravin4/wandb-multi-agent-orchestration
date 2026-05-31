"""Report agent — full session debrief with weave.Evaluation as the money shot."""

from __future__ import annotations

import json
import re

import weave
from langchain_core.messages import HumanMessage, SystemMessage

from app.services.llm import get_llm
from app.state import QuestionResult


@weave.op()
def _score_question(output: dict, **kwargs) -> dict:
    """Per-question scorer for weave.Evaluation; ``output`` is one QuestionResult row."""
    content = output.get("content_score", 0)
    delivery = output.get("delivery_score", 0)
    return {
        "content": content,
        "delivery": delivery,
        "overall": round((content + delivery) / 2, 2),
    }


@weave.op()
def generate_report(results: list[QuestionResult], session_id: str) -> dict:
    """Synthesize all question scores into a final debrief and log weave.Evaluation."""
    if not results:
        return {"error": "no results to report"}

    avg_content = round(sum(r["content_score"] for r in results) / len(results), 2)
    avg_delivery = round(sum(r["delivery_score"] for r in results) / len(results), 2)
    avg_overall = round((avg_content + avg_delivery) / 2, 2)

    results_summary = "\n".join(
        f"Q{r['question_index'] + 1} ({r['question_type']}): "
        f"content={r['content_score']}/10, delivery={r['delivery_score']}/10 "
        f"| {r.get('feedback', '')}"
        for r in results
    )

    llm = get_llm("synthesis")
    response = llm.invoke([
        SystemMessage(content=(
            "You are a senior interview coach writing a concise post-session debrief. "
            "Be specific and actionable — name exact skills and concrete actions. "
            "Return only valid JSON:\n"
            '{"summary": "<2 sentences overall>", '
            '"strengths": ["<specific strength>", "<specific strength>"], '
            '"areas_to_improve": ["<specific gap>", "<specific gap>"], '
            '"next_steps": ["<concrete action>", "<concrete action>", "<concrete action>"]}'
        )),
        HumanMessage(content=(
            f"Session: {len(results)} questions answered\n"
            f"Avg content score: {avg_content}/10\n"
            f"Avg delivery score: {avg_delivery}/10\n\n"
            f"Per-question breakdown:\n{results_summary}"
        )),
    ])

    raw = response.content if isinstance(response.content, str) else str(response.content)
    match = re.search(r"\{[\s\S]*\}", raw)
    parsed = json.loads(match.group()) if match else {}

    # weave.Evaluation — links all question traces as a structured session summary
    dataset = weave.Dataset(
        name=f"session-{session_id[:8]}",
        rows=[dict(r) for r in results],
    )
    evaluation = weave.Evaluation(
        name=f"session-eval-{session_id[:8]}",
        dataset=dataset,
        scorers=[_score_question],
    )
    weave.publish(evaluation)

    return {
        "summary": parsed.get("summary", ""),
        "strengths": parsed.get("strengths", []),
        "areas_to_improve": parsed.get("areas_to_improve", []),
        "next_steps": parsed.get("next_steps", []),
        "avg_content_score": avg_content,
        "avg_delivery_score": avg_delivery,
        "avg_overall": avg_overall,
    }
