"""Session persistence — Upstash Redis with in-memory fallback.

In production (Render), set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN.
In local dev, if those vars are absent, falls back to an in-memory dict.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from app.state import SessionState

logger = logging.getLogger(__name__)

_SESSION_TTL = 86400  # 24 hours

_redis = None
_redis_checked = False
_memory: dict[str, SessionState] = {}


def _get_redis():
    global _redis, _redis_checked
    if _redis_checked:
        return _redis

    _redis_checked = True

    from app.config import get_settings
    settings = get_settings()

    if not settings.upstash_redis_url or not settings.upstash_redis_token:
        logger.warning(
            "UPSTASH_REDIS_REST_URL / UPSTASH_REDIS_REST_TOKEN not set — "
            "using in-memory session store (sessions lost on restart)"
        )
        return None

    from upstash_redis import Redis
    _redis = Redis(url=settings.upstash_redis_url, token=settings.upstash_redis_token)
    logger.info("Upstash Redis session store connected")
    return _redis


def get_session(session_id: str) -> Optional[SessionState]:
    redis = _get_redis()
    if redis is None:
        return _memory.get(session_id)

    data = redis.get(session_id)
    if data is None:
        return None
    return json.loads(data)


def set_session(session_id: str, state: SessionState) -> None:
    redis = _get_redis()
    if redis is None:
        _memory[session_id] = state
        return

    redis.set(session_id, json.dumps(state), ex=_SESSION_TTL)


def delete_session(session_id: str) -> None:
    redis = _get_redis()
    if redis is None:
        _memory.pop(session_id, None)
        return

    redis.delete(session_id)
