"""Sliding-window rate limiter — Redis when available, in-process fallback.

Production multi-worker / multi-replica deployments must use Redis (same URL as
the rest of the stack). The in-memory backend is only safe for single-process
local demos and pytest.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from functools import lru_cache
from threading import Lock

from app.core.config import settings


@lru_cache
def _redis():
    try:
        from redis import Redis

        client = Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=0.4)
        client.ping()
        return client
    except Exception:
        return None


class SlidingWindowLimiter:
    """Thread-safe sliding window: allow at most `limit` hits per `window_seconds`."""

    def __init__(self, *, redis_prefix: str) -> None:
        self._prefix = redis_prefix
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _redis_key(self, key: str) -> str:
        return f"rl:{self._prefix}:{key}"

    def over_limit(self, key: str, *, limit: int, window_seconds: float) -> bool:
        """True if key is already at/over the limit (does not record a hit)."""
        r = _redis()
        if r is not None:
            try:
                rk = self._redis_key(key)
                now = time.time()
                cutoff = now - window_seconds
                pipe = r.pipeline()
                pipe.zremrangebyscore(rk, 0, cutoff)
                pipe.zcard(rk)
                _, count = pipe.execute()
                return int(count) >= limit
            except Exception:
                pass
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            q = self._events[key]
            while q and q[0] < cutoff:
                q.popleft()
            return len(q) >= limit

    def hit(self, key: str, *, limit: int, window_seconds: float) -> bool:
        """Record an attempt. Returns True if under the limit, False if exceeded."""
        r = _redis()
        if r is not None:
            try:
                rk = self._redis_key(key)
                now = time.time()
                cutoff = now - window_seconds
                member = f"{now}:{time.time_ns()}"
                pipe = r.pipeline()
                pipe.zremrangebyscore(rk, 0, cutoff)
                pipe.zcard(rk)
                count = pipe.execute()[1]
                if int(count) >= limit:
                    return False
                pipe = r.pipeline()
                pipe.zadd(rk, {member: now})
                pipe.expire(rk, int(window_seconds) + 5)
                pipe.execute()
                return True
            except Exception:
                pass
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            q = self._events[key]
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True

    def reset(self, key: str) -> None:
        r = _redis()
        if r is not None:
            try:
                r.delete(self._redis_key(key))
            except Exception:
                pass
        with self._lock:
            self._events.pop(key, None)


# Shared limiters. Prefer Redis when reachable (horizontal scale).
login_ip_limiter = SlidingWindowLimiter(redis_prefix="login_ip")
login_email_limiter = SlidingWindowLimiter(redis_prefix="login_email")
totp_verify_limiter = SlidingWindowLimiter(redis_prefix="totp")

# Defaults aligned with PERMISSIONS.md (login counters applied to failed attempts).
LOGIN_IP_LIMIT = 10
LOGIN_IP_WINDOW_SECONDS = 60.0
LOGIN_EMAIL_LIMIT = 5
LOGIN_EMAIL_WINDOW_SECONDS = 60.0
TOTP_VERIFY_LIMIT = 5
TOTP_VERIFY_WINDOW_SECONDS = 300.0  # pending-2FA token lifetime
