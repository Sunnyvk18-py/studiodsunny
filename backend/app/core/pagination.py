"""Cursor-based list pagination with a hard server-side cap.

Lists must never be unbounded. Prefer `before` (created_at cursor) over offset.
Hard max is enforced even if a client asks for more.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import Query
from sqlalchemy import Select

HARD_MAX = 100
DEFAULT_LIMIT = 50


def clamp_limit(limit: int | None, *, default: int = DEFAULT_LIMIT, hard_max: int = HARD_MAX) -> int:
    if limit is None:
        return default
    return max(1, min(int(limit), hard_max))


def LimitQuery(default: int = DEFAULT_LIMIT, hard_max: int = HARD_MAX):
    """FastAPI Query with documented hard max (le=hard_max)."""
    return Query(default, ge=1, le=hard_max, description=f"Page size (hard max {hard_max})")


def apply_created_before_cursor(stmt: Select, model: type, before: datetime | None) -> Select:
    """Keyset page: rows strictly older than `before` (DESC created_at pages)."""
    if before is not None:
        stmt = stmt.where(model.created_at < before)
    return stmt.order_by(model.created_at.desc(), model.id.desc())
