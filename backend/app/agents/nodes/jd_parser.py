"""JD Parser agent — structured extraction of signals from the job description."""

from __future__ import annotations

import json
import re

import weave
from langchain_core.messages import HumanMessage, SystemMessage

from app.services.llm import get_llm
from app.state import SessionState


@weave.op()
def jd_parser_node(state: SessionState) -> SessionState:
    """Extract structured technical and behavioral signals from the raw JD."""
    llm = get_llm("fast")
    response = llm.invoke([
        SystemMessage(content=(
            "Extract structured signals from this job description. "
            "Return only valid JSON with these exact keys:\n"
            '{"company": "<company name, or empty string if unclear>", '
            '"role": "<exact job title>", '
            '"seniority": "<junior|mid|senior|staff|principal>", '
            '"tech_stack": ["<specific technology>", ...], '
            '"required_skills": ["<skill>", ...], '
            '"behavioral_themes": ["<theme e.g. ownership, collaboration, customer focus>", ...], '
            '"domain_focus": "<e.g. ml infrastructure, backend systems, developer tools>"}'
        )),
        HumanMessage(content=state.get("job_description", "")),
    ])

    raw = response.content if isinstance(response.content, str) else str(response.content)
    match = re.search(r"\{[\s\S]*\}", raw)
    parsed = json.loads(match.group()) if match else {}

    updates: dict = {"jd_parsed": parsed}

    # Fill in company/role/seniority only if the form fields were left empty
    if not state.get("company") and parsed.get("company"):
        updates["company"] = parsed["company"]
    if not state.get("role") and parsed.get("role"):
        updates["role"] = parsed["role"]
    if parsed.get("seniority"):
        updates["seniority"] = parsed["seniority"]

    return {**state, **updates}
