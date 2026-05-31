"""Evaluation datasets for the Format agent.

Each row supplies the research context the Format agent consumes, so the eval
runs deterministically without hitting Tavily. Extend or version this list as
the agent graph grows (jd_parser, interviewer, delivery, report).
"""

from __future__ import annotations

from typing import TypedDict


class FormatEvalSample(TypedDict):
    session_id: str
    job_description: str
    company: str
    role: str
    interview_format: str
    common_topics: list[str]


JD_SAMPLES: list[FormatEvalSample] = [
    {
        "session_id": "eval-backend-001",
        "job_description": (
            "Senior Backend Engineer to design and operate high-throughput "
            "payment APIs in Python and Go. Owns service reliability, on-call, "
            "and data modeling for a ledger system."
        ),
        "company": "Stripe",
        "role": "Senior Backend Engineer",
        "interview_format": (
            "Stripe runs a practical coding round (API design / debugging in "
            "your language), a system design round focused on payments and "
            "consistency, and a behavioral round on ownership and incident response."
        ),
        "common_topics": [
            "idempotent API design",
            "distributed transactions",
            "on-call / incident response",
            "data modeling for ledgers",
        ],
    },
    {
        "session_id": "eval-frontend-001",
        "job_description": (
            "Frontend Engineer (React/TypeScript) building accessible, "
            "performant dashboards. Cares about component design and Core Web Vitals."
        ),
        "company": "Vercel",
        "role": "Frontend Engineer",
        "interview_format": (
            "A take-home-style live coding round building a React component, a "
            "front-end system design round (rendering, caching, accessibility), "
            "and a behavioral round on collaboration."
        ),
        "common_topics": [
            "React rendering and state",
            "web performance / Core Web Vitals",
            "accessibility",
            "component API design",
        ],
    },
    {
        "session_id": "eval-ml-001",
        "job_description": (
            "Machine Learning Engineer to productionize LLM features: retrieval, "
            "evaluation harnesses, and latency optimization for inference."
        ),
        "company": "Anthropic",
        "role": "ML Engineer",
        "interview_format": (
            "A coding round on data/ML tooling, a system design round on serving "
            "and evaluating ML systems at scale, and a behavioral round."
        ),
        "common_topics": [
            "retrieval-augmented generation",
            "model evaluation",
            "inference latency / batching",
            "experiment tracking",
        ],
    },
]
