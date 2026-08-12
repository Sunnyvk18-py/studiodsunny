"""Access-token jti denylist. Redis when available, in-memory fallback for local demo."""

from __future__ import annotations

import time
from functools import lru_cache

from app.core.config import settings

_memory: dict[str, float] = {}


@lru_cache
def _redis():
    try:
        from redis import Redis

        client = Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=0.4)
        client.ping()
        return client
    except Exception:
        return None


def deny_jti(jti: str, ttl_seconds: int) -> None:
    if not jti or ttl_seconds <= 0:
        return
    r = _redis()
    if r is not None:
        try:
            r.setex(f"jti:{jti}", ttl_seconds, "1")
            return
        except Exception:
            pass
    _memory[jti] = time.time() + ttl_seconds


def is_denied(jti: str | None) -> bool:
    if not jti:
        return False
    r = _redis()
    if r is not None:
        try:
            return bool(r.exists(f"jti:{jti}"))
        except Exception:
            pass
    exp = _memory.get(jti)
    if exp is None:
        return False
    if exp < time.time():
        _memory.pop(jti, None)
        return False
    return True
