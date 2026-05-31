"""Research agent node — uses jd_parser signals for a targeted Tavily query."""

from __future__ import annotations

import weave

from app.observability import log_research_metrics
from app.services.llm import get_llm
from app.services.research import search
from app.state import SessionState


@weave.op()
def research_node(state: SessionState) -> SessionState:
    """Research company interview format using structured signals from jd_parser."""
    company = state.get("company", "")
    role = state.get("role", "")
    jd_parsed = state.get("jd_parsed", {})

    # Use jd_parser's extracted signals to build a targeted search query
    tech_stack = jd_parsed.get("tech_stack", [])
    domain_focus = jd_parsed.get("domain_focus", "")
    tech_str = " ".join(tech_stack[:3]) if tech_stack else ""
    query = f"{company} {role} {tech_str} {domain_focus} interview process format questions".strip()

    results = search(query, max_results=5)
    snippets = "\n".join(
        f"- {r.get('title', 'Untitled')}: {r.get('content', '')[:300]}"
        for r in results
    )

    llm = get_llm("default")
    response = llm.invoke([
        {
            "role": "system",
            "content": (
                "You summarize interview research for a mock interview prep session. "
                "Return a short interview_format paragraph and a bullet list of common_topics."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Job: {state.get('job_description', '')}\n\n"
                f"Key skills from JD: {jd_parsed.get('required_skills', [])}\n"
                f"Tech stack: {tech_stack}\n"
                f"Behavioral themes: {jd_parsed.get('behavioral_themes', [])}\n\n"
                f"Research:\n{snippets}"
            ),
        },
    ])

    text = response.content if isinstance(response.content, str) else str(response.content)
    interview_format = text[:500]
    common_topics = [line.strip("- ").strip() for line in text.splitlines() if line.strip().startswith("-")][:10]

    log_research_metrics(interview_format, common_topics)

    return {
        "interview_format": interview_format,
        "common_topics": common_topics or ["general behavioral", "technical depth"],
    }
