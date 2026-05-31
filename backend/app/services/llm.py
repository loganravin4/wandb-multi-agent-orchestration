"""W&B Serverless Inference client (OpenAI-compatible).

All agents call Claude-free models hosted on W&B Serverless Inference. The
OpenAI SDK is pointed at the W&B endpoint and authenticated with the W&B API
key, so no Anthropic key is required. Calls are auto-traced by Weave.
"""

from __future__ import annotations

from functools import lru_cache

import openai

from app.config import get_settings


@lru_cache
def get_client() -> openai.OpenAI:
    """OpenAI client bound to the W&B Serverless Inference endpoint."""
    settings = get_settings()
    project = (
        f"{settings.wandb_entity}/{settings.wandb_project}"
        if settings.wandb_entity
        else settings.wandb_project
    )
    return openai.OpenAI(
        base_url=settings.inference_base_url,
        api_key=settings.wandb_api_key,
        # W&B repurposes the OpenAI `project` kwarg ("<entity>/<project>") to
        # attribute inference usage and Weave traces to the right project.
        project=project,
    )


def complete(
    messages: list[dict[str, str]],
    *,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """Run a chat completion and return the assistant text."""
    response = get_client().chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""
