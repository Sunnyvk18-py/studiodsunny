"""Hostile seed: every GET as each role — no 5xx, valid JSON, size & timing bounds."""

from __future__ import annotations

import json
import time
from typing import Iterable

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.seed.seed import DEMO_PASSWORD, run_demo as seed_run

pytestmark = pytest.mark.hostile

seed_run()

ROLES = {
    "founder": "sunny@studiosunny.com",
    "pm": "arjun@studiosunny.com",
    "developer": "rahul@studiosunny.com",
    "designer": "priya@studiosunny.com",
}

MAX_BYTES = 5 * 1024 * 1024
MAX_SECONDS = 2.0
TIMING_EXEMPT: set[str] = set()
LIST_HARD_MAX = 100


@pytest.fixture(scope="module")
def hostile_ids():
    from app.db.session import SessionLocal
    from tests.fixtures.hostile_seed import load_hostile_seed

    db = SessionLocal()
    try:
        return load_hostile_seed(db)
    finally:
        db.close()


def _client_for(email: str) -> TestClient:
    c = TestClient(app)
    res = c.post("/api/v1/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    assert res.status_code == 200, res.text
    csrf = res.json().get("csrf_token")
    if csrf:
        c.headers["X-CSRF-Token"] = csrf
    return c


def _get_routes(hostile_ids: dict) -> list[str]:
    """All GET paths we can call without inventing unknown IDs."""
    pid = hostile_ids["huge_project_id"]
    empty = hostile_ids["empty_project_id"]
    slug = hostile_ids["channel_slug"]
    return [
        "/health",
        "/api/v1/auth/me",
        "/api/v1/auth/providers",
        "/api/v1/auth/sessions",
        "/api/v1/dashboard",
        "/api/v1/desk",
        "/api/v1/calendar/events",
        "/api/v1/activity",
        "/api/v1/search?q=Hostile",
        "/api/v1/notifications",
        "/api/v1/ai/briefing",
        "/api/v1/clients",
        "/api/v1/leads",
        "/api/v1/invoices",
        "/api/v1/reports",
        "/api/v1/projects",
        f"/api/v1/projects/{pid}",
        f"/api/v1/projects/{empty}",
        "/api/v1/tasks",
        "/api/v1/employees",
        "/api/v1/employees/departments",
        "/api/v1/employees/roles",
        "/api/v1/chat/channels",
        f"/api/v1/chat/channels/{slug}/messages?limit=50",
        "/api/v1/docs",
        "/api/v1/files",
        "/api/v1/audit",
        "/api/v1/admin/settings",
        "/api/v1/admin/permissions",
        "/api/v1/admin/integrations",
        "/api/v1/admin/templates",
    ]


@pytest.mark.parametrize("role,email", list(ROLES.items()))
def test_hostile_gets_no_5xx_json_bounded(role: str, email: str, hostile_ids: dict):
    client = _client_for(email)
    slow: list[str] = []
    fat: list[str] = []
    bad: list[str] = []

    for path in _get_routes(hostile_ids):
        t0 = time.perf_counter()
        res = client.get(path)
        elapsed = time.perf_counter() - t0
        if res.status_code >= 500:
            bad.append(f"{path} → {res.status_code}")
            continue
        # JSON endpoints (skip empty 204)
        if res.status_code != 204 and res.content:
            ctype = res.headers.get("content-type", "")
            if "application/json" in ctype:
                try:
                    json.loads(res.content)
                except Exception:
                    bad.append(f"{path} invalid JSON")
            if len(res.content) > MAX_BYTES:
                fat.append(f"{path} {len(res.content)} bytes")
        if elapsed > MAX_SECONDS and path.split("?")[0] not in TIMING_EXEMPT:
            slow.append(f"{path} {elapsed:.2f}s")

    assert not bad, f"{role} failures:\n" + "\n".join(bad)
    assert not fat, f"{role} oversized responses:\n" + "\n".join(fat)
    assert not slow, f"{role} slow endpoints (> {MAX_SECONDS}s) — likely N+1:\n" + "\n".join(slow)

    # Cursor pagination hard cap — hostile seed has ≥5k tasks; unbounded would be multi-MB.
    tasks = client.get("/api/v1/tasks")
    if tasks.status_code == 200:
        body = tasks.json()
        assert isinstance(body, list)
        assert len(body) <= LIST_HARD_MAX, f"/tasks returned {len(body)} rows (cap {LIST_HARD_MAX})"
    over = client.get("/api/v1/tasks?limit=5000")
    if over.status_code == 422:
        pass  # FastAPI le=HARD_MAX rejects
    elif over.status_code == 200:
        assert len(over.json()) <= LIST_HARD_MAX


def test_hostile_seed_created_volume(hostile_ids: dict):
    from sqlalchemy import func, select

    from app.db.session import SessionLocal
    from app.models.chat import ChatMessage
    from app.models.task import Task
    from uuid import UUID

    db = SessionLocal()
    try:
        n_tasks = db.scalar(
            select(func.count()).select_from(Task).where(Task.project_id == UUID(hostile_ids["huge_project_id"]))
        )
        assert n_tasks >= 5000
        n_msgs = db.scalar(select(func.count()).select_from(ChatMessage))
        assert n_msgs >= 10_000
    finally:
        db.close()
