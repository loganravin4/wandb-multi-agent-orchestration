"""Offline Weave evaluation of the Format agent.

Runs the Format agent over a fixed dataset of research contexts and logs each
prediction + scores to Weave via EvaluationLogger, so results show up under
the project's Evals tab and coding agents can hill-climb them via the MCP.

Run (Docker):
    docker compose run --rm backend python -m app.evals.run_eval

Run (local):
    python -m app.evals.run_eval
"""

from __future__ import annotations

from weave import EvaluationLogger

from app.agents.nodes.format import format_node
from app.evals.datasets import JD_SAMPLES, FormatEvalSample
from app.evals.scorers import question_count_ok, relevance_judge, schema_validity
from app.observability import init_weave

SCORERS = ("question_count_ok", "schema_validity", "relevance")


def _evaluate_sample(sample: FormatEvalSample) -> tuple[list, dict[str, float]]:
    """Run the Format agent on one sample and compute its scores."""
    state = {**sample, "phase": "interview"}
    try:
        questions = format_node(state).get("questions", [])
    except Exception as exc:  # a crash on a sample is itself a failure to score
        print(f"  ! {sample['session_id']} raised {exc!r}; scoring 0")
        questions = []

    scores = {
        "question_count_ok": question_count_ok(questions),
        "schema_validity": schema_validity(questions),
        "relevance": relevance_judge(sample["job_description"], questions),
    }
    return questions, scores


def main() -> None:
    init_weave()

    eval_logger = EvaluationLogger(model="format-agent", dataset="jd-samples-v1")
    totals: dict[str, float] = {name: 0.0 for name in SCORERS}

    for sample in JD_SAMPLES:
        questions, scores = _evaluate_sample(sample)

        pred = eval_logger.log_prediction(
            inputs={
                "company": sample["company"],
                "role": sample["role"],
                "job_description": sample["job_description"],
            },
            output=questions,
        )
        for name in SCORERS:
            pred.log_score(scorer=name, score=scores[name])
            totals[name] += scores[name]
        pred.finish()

        print(f"  {sample['session_id']}: " + ", ".join(f"{n}={scores[n]:.2f}" for n in SCORERS))

    n = len(JD_SAMPLES)
    summary = {f"{name}_avg": totals[name] / n for name in SCORERS}
    eval_logger.log_summary(summary)
    print("Summary:", ", ".join(f"{k}={v:.2f}" for k, v in summary.items()))


if __name__ == "__main__":
    main()
