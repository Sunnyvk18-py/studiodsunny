"""Cursor pagination helpers — hard server cap must never be bypassed."""

from app.core.pagination import HARD_MAX, clamp_limit


def test_clamp_limit_hard_max():
    assert clamp_limit(None) == 50
    assert clamp_limit(1) == 1
    assert clamp_limit(HARD_MAX) == HARD_MAX
    assert clamp_limit(HARD_MAX + 1) == HARD_MAX
    assert clamp_limit(50_000) == HARD_MAX
    assert clamp_limit(0) == 1
