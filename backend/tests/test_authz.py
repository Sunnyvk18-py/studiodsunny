"""Authorization tests derived from PERMISSIONS.md (source of truth).

These tests assert the matrix — not current implementation quirks.
Role mapping: pm → project_manager; developer/designer as seeded.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.seed.seed import DEMO_PASSWORD, run_demo as seed_run

seed_run()

PERMISSIONS_MD = Path(__file__).resolve().parents[2] / "PERMISSIONS.md"
PREFIX = "/api/v1"

FOUNDER = "sunny@studiosunny.com"
PM = "arjun@studiosunny.com"
DEVELOPER = "rahul@studiosunny.com"
DESIGNER = "priya@studiosunny.com"

# Paths documented in PERMISSIONS.md (normalized, no trailing slash)
DOCUMENTED_PATHS = {
    "/health",
    f"{PREFIX}/auth/login",
    f"{PREFIX}/auth/refresh",
    f"{PREFIX}/auth/logout",
    f"{PREFIX}/auth/providers",
    f"{PREFIX}/auth/2fa/verify",
    f"{PREFIX}/auth/google/start",
    f"{PREFIX}/auth/google/callback",
    f"{PREFIX}/auth/forgot-password",
    f"{PREFIX}/auth/reset-password",
    f"{PREFIX}/auth/invite/{{token}}",
    f"{PREFIX}/auth/accept-invite",
    f"{PREFIX}/auth/me",
    f"{PREFIX}/auth/logout-all",
    f"{PREFIX}/auth/change-password",
    f"{PREFIX}/auth/2fa/setup",
    f"{PREFIX}/auth/2fa/enable",
    f"{PREFIX}/auth/2fa/disable",
    f"{PREFIX}/auth/sessions",
    f"{PREFIX}/auth/sessions/{{id}}",
    f"{PREFIX}/dashboard",
    f"{PREFIX}/desk",
    f"{PREFIX}/calendar/events",
    f"{PREFIX}/activity",
    f"{PREFIX}/search",
    f"{PREFIX}/notifications",
    f"{PREFIX}/notifications/{{id}}/read",
    f"{PREFIX}/notifications/read-all",
    f"{PREFIX}/ai/briefing",
    f"{PREFIX}/ai/ask",
    f"{PREFIX}/clients",
    f"{PREFIX}/clients/{{id}}",
    f"{PREFIX}/clients/{{id}}/archive",
    f"{PREFIX}/leads",
    f"{PREFIX}/invoices",
    f"{PREFIX}/invoices/{{id}}",
    f"{PREFIX}/reports",
    f"{PREFIX}/projects",
    f"{PREFIX}/projects/{{id}}",
    f"{PREFIX}/projects/{{id}}/archive",
    f"{PREFIX}/projects/{{id}}/milestones",
    f"{PREFIX}/tasks",
    f"{PREFIX}/tasks/{{id}}",
    f"{PREFIX}/tasks/{{id}}/archive",
    f"{PREFIX}/tasks/{{id}}/comments",
    f"{PREFIX}/tasks/{{id}}/comments/{{comment_id}}",
    f"{PREFIX}/employees",
    f"{PREFIX}/employees/{{id}}",
    f"{PREFIX}/employees/departments",
    f"{PREFIX}/employees/roles",
    f"{PREFIX}/employees/invite",
    f"{PREFIX}/chat/channels",
    f"{PREFIX}/chat/channels/{{slug}}/messages",
    f"{PREFIX}/chat/channels/{{slug}}/messages/{{id}}",
    f"{PREFIX}/chat/ws",
    f"{PREFIX}/docs",
    f"{PREFIX}/docs/{{id}}",
    f"{PREFIX}/docs/{{id}}/yjs",
    f"{PREFIX}/docs/{{id}}/collab",
    f"{PREFIX}/files",
    f"{PREFIX}/files/{{id}}",
    f"{PREFIX}/files/{{id}}/download",
    f"{PREFIX}/audit",
    f"{PREFIX}/admin/settings",
    f"{PREFIX}/admin/permissions",
    f"{PREFIX}/admin/permissions/overrides",
    f"{PREFIX}/admin/integrations",
    f"{PREFIX}/admin/templates",
    f"{PREFIX}/admin/templates/{{id}}",
}


def _client() -> TestClient:
    return TestClient(app)


def _login(c: TestClient, email: str, password: str = DEMO_PASSWORD) -> dict:
    res = c.post(f"{PREFIX}/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    csrf = res.json().get("csrf_token")
    if csrf:
        c.headers["X-CSRF-Token"] = csrf
    return res.json()


def _normalize_path(path: str) -> str:
    """Turn FastAPI path templates into matrix-style templates."""
    out = re.sub(r"\{[^}:]+:[^}]+\}", lambda m: "{" + m.group(0).split(":")[0][1:] + "}", path)
    # unify common param names
    out = out.replace("{doc_id}", "{id}").replace("{file_id}", "{id}")
    out = out.replace("{client_id}", "{id}").replace("{project_id}", "{id}")
    out = out.replace("{task_id}", "{id}").replace("{employee_id}", "{id}")
    out = out.replace("{notification_id}", "{id}").replace("{invoice_id}", "{id}")
    out = out.replace("{message_id}", "{id}").replace("{comment_id}", "{comment_id}")
    out = out.replace("{template_id}", "{id}")
    return out


def _anon_with_csrf() -> TestClient:
    """CSRF-capable anonymous client so middleware does not mask 401s on mutating routes."""
    c = _client()
    token = "test-csrf-anon"
    c.cookies.set("ss_csrf", token)
    c.headers["X-CSRF-Token"] = token
    return c


def _founder_client_id(founder: TestClient) -> str:
    clients = founder.get(f"{PREFIX}/clients").json()
    assert clients
    return clients[0]["id"]


def _hidden_project(founder: TestClient, *, member_ids: list | None = None) -> dict:
    created = founder.post(
        f"{PREFIX}/projects",
        json={
            "name": f"Authz Hidden {uuid.uuid4().hex[:6]}",
            "client_id": _founder_client_id(founder),
            "project_type": "Website",
            "member_ids": member_ids or [],
            "priority": "low",
        },
    )
    assert created.status_code == 201, created.text
    return created.json()


def _user_id(c: TestClient, email: str) -> str:
    people = c.get(f"{PREFIX}/employees").json()
    row = next(p for p in people if p.get("email") == email)
    return row["user_id"]


# --- Route coverage ---


def test_route_coverage_guard():
    """Every mounted API route must appear in PERMISSIONS.md."""
    text = PERMISSIONS_MD.read_text(encoding="utf-8")
    undocumented = []
    for route in app.routes:
        path = getattr(route, "path", None)
        if not path or not (path.startswith("/api/v1") or path == "/health"):
            continue
        probe = path
        for name in (
            "doc_id",
            "file_id",
            "client_id",
            "project_id",
            "task_id",
            "employee_id",
            "notification_id",
            "template_id",
            "message_id",
            "invoice_id",
        ):
            probe = probe.replace("{" + name + "}", "{id}")
        probe = probe.replace("{slug}", "{slug}").replace("{token}", "{token}")
        if "/api/v1" in probe or probe == "/health":
            short = probe if probe == "/health" else probe
            norm = _normalize_path(path).replace("{invoice_id}", "{id}")
            if short not in text and norm not in text and probe not in text:
                if norm not in text and path.replace("{doc_id}", "{id}") not in text:
                    undocumented.append(path)
    assert not undocumented, f"Routes missing from PERMISSIONS.md: {undocumented}"


def test_documented_paths_include_new_routes():
    for path in (
        f"{PREFIX}/auth/sessions",
        f"{PREFIX}/auth/sessions/{{id}}",
        f"{PREFIX}/invoices/{{id}}",
        f"{PREFIX}/tasks/{{id}}/comments/{{comment_id}}",
        f"{PREFIX}/chat/channels/{{slug}}/messages/{{id}}",
    ):
        assert path in DOCUMENTED_PATHS


# --- Session semantics ---


def test_unauthenticated_gets_401():
    c = _client()
    for path in (
        f"{PREFIX}/auth/me",
        f"{PREFIX}/dashboard",
        f"{PREFIX}/clients",
        f"{PREFIX}/invoices",
        f"{PREFIX}/audit",
        f"{PREFIX}/projects",
        f"{PREFIX}/employees",
    ):
        res = c.get(path)
        assert res.status_code == 401, f"{path} → {res.status_code}"


def test_public_logout_idempotent():
    c = _client()
    res = c.post(f"{PREFIX}/auth/logout")
    assert res.status_code == 204


# --- Public routes ---


def test_public_providers_no_session():
    c = _client()
    res = c.get(f"{PREFIX}/auth/providers")
    assert res.status_code == 200
    body = res.json()
    assert "google" in body


def test_public_google_start_state_or_501():
    c = _client()
    res = c.get(f"{PREFIX}/auth/google/start", follow_redirects=False)
    if res.status_code == 501:
        return
    assert res.status_code in (302, 307), res.text
    loc = res.headers.get("location") or ""
    assert "state=" in loc


def test_login_rate_limit_email_bucket():
    from app.core.rate_limit import LOGIN_EMAIL_LIMIT, login_email_limiter

    email = f"ratelimit-{uuid.uuid4().hex[:10]}@studiosunny.com"
    c = _client()
    statuses = []
    for _ in range(LOGIN_EMAIL_LIMIT + 2):
        res = c.post(f"{PREFIX}/auth/login", json={"email": email, "password": "wrong-password-xx"})
        statuses.append(res.status_code)
    login_email_limiter.reset(f"login:email:{email}")
    assert 429 in statuses, statuses
    assert statuses[-1] == 429


# --- Sessions ---


def test_sessions_list_401_and_200():
    anon = _client()
    assert anon.get(f"{PREFIX}/auth/sessions").status_code == 401

    c = _client()
    _login(c, FOUNDER)
    res = c.get(f"{PREFIX}/auth/sessions")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    assert any(s.get("current") for s in res.json())


def test_delete_foreign_session_404():
    sunny = _client()
    _login(sunny, FOUNDER)
    sessions = sunny.get(f"{PREFIX}/auth/sessions").json()
    assert sessions
    sid = sessions[0]["id"]

    rahul = _client()
    _login(rahul, DEVELOPER)
    res = rahul.delete(f"{PREFIX}/auth/sessions/{sid}")
    assert res.status_code == 404
    missing = rahul.delete(f"{PREFIX}/auth/sessions/{uuid.uuid4()}")
    assert missing.status_code == 404
    assert res.json() == missing.json()


# --- Workspace 401 ---


@pytest.mark.parametrize(
    "method,path,json_body",
    [
        ("GET", f"{PREFIX}/desk", None),
        ("GET", f"{PREFIX}/calendar/events", None),
        ("GET", f"{PREFIX}/activity", None),
        ("GET", f"{PREFIX}/notifications", None),
        ("GET", f"{PREFIX}/ai/briefing", None),
        ("POST", f"{PREFIX}/ai/ask", {"question": "What is on my desk?"}),
        ("GET", f"{PREFIX}/search", None),
        ("POST", f"{PREFIX}/notifications/read-all", None),
        ("GET", f"{PREFIX}/auth/me", None),
        ("GET", f"{PREFIX}/auth/sessions", None),
        ("POST", f"{PREFIX}/auth/logout-all", None),
        ("POST", f"{PREFIX}/auth/2fa/setup", None),
        ("GET", f"{PREFIX}/projects", None),
        ("GET", f"{PREFIX}/tasks", None),
        ("GET", f"{PREFIX}/employees", None),
        ("GET", f"{PREFIX}/employees/departments", None),
        ("GET", f"{PREFIX}/employees/roles", None),
        ("GET", f"{PREFIX}/chat/channels", None),
        ("GET", f"{PREFIX}/docs", None),
        ("GET", f"{PREFIX}/files", None),
        ("GET", f"{PREFIX}/dashboard", None),
    ],
)
def test_session_required_routes_401(method: str, path: str, json_body):
    c = _anon_with_csrf() if method != "GET" else _client()
    if method == "GET":
        res = c.get(path)
    else:
        res = c.post(path, json=json_body or {})
    assert res.status_code == 401, f"{method} {path} → {res.status_code}"


# --- Founder-gated cash / admin ---


def test_developer_denied_clients_invoices_reports_audit_admin():
    c = _client()
    _login(c, DEVELOPER)
    assert c.get(f"{PREFIX}/clients").status_code == 403
    assert c.get(f"{PREFIX}/invoices").status_code == 403
    assert c.get(f"{PREFIX}/reports").status_code == 403
    assert c.get(f"{PREFIX}/audit").status_code == 403
    assert c.get(f"{PREFIX}/admin/settings").status_code == 403
    assert c.get(f"{PREFIX}/leads").status_code == 403


def test_designer_denied_clients_and_cash():
    c = _client()
    _login(c, DESIGNER)
    assert c.get(f"{PREFIX}/clients").status_code == 403
    assert c.get(f"{PREFIX}/invoices").status_code == 403


def test_pm_can_clients_not_invoices_or_audit():
    c = _client()
    _login(c, PM)
    assert c.get(f"{PREFIX}/clients").status_code == 200
    assert c.get(f"{PREFIX}/leads").status_code == 200
    assert c.get(f"{PREFIX}/invoices").status_code == 403
    assert c.get(f"{PREFIX}/audit").status_code == 403
    assert c.get(f"{PREFIX}/admin/settings").status_code == 403


def test_dashboard_cash_founder_only():
    founder = _client()
    _login(founder, FOUNDER)
    f_dash = founder.get(f"{PREFIX}/dashboard").json()

    dev = _client()
    _login(dev, DEVELOPER)
    d_dash = dev.get(f"{PREFIX}/dashboard").json()

    # Founder payload may include finance fields; developer must not see cash figures
    blob = str(d_dash).lower()
    for key in ("outstanding", "revenue", "pipeline_value", "cash", "invoices_total"):
        if key in f_dash or key in str(f_dash).lower():
            assert key not in blob or d_dash.get(key) in (None, 0, 0.0, [], {})


def test_employee_payload_reduced_for_non_founder():
    c = _client()
    _login(c, DEVELOPER)
    people = c.get(f"{PREFIX}/employees").json()
    assert people
    for row in people:
        if row.get("email") == DEVELOPER:
            continue  # self may see own compensation
        assert row.get("salary") is None
        assert row.get("phone") in (None, "")


def test_self_patch_cannot_escalate():
    c = _client()
    me = _login(c, DEVELOPER)
    emp_id = None
    people = c.get(f"{PREFIX}/employees").json()
    for row in people:
        if row.get("email") == DEVELOPER:
            emp_id = row["id"]
            break
    assert emp_id
    before = c.get(f"{PREFIX}/employees/{emp_id}").json()
    res = c.patch(
        f"{PREFIX}/employees/{emp_id}",
        json={
            "role_key": "founder",
            "salary": 999999,
            "department_id": None,
            "is_active": False,
            "display_name": before.get("display_name") or "Rahul",
        },
    )
    assert res.status_code == 200, res.text
    after = res.json()
    assert after.get("role_key") == before.get("role_key")
    assert after.get("is_active") is not False
    assert after.get("salary") in (None, before.get("salary"))


# --- Clients wrong role ---


@pytest.mark.parametrize("email", [DEVELOPER, DESIGNER])
def test_clients_post_wrong_role_403(email: str):
    c = _client()
    _login(c, email)
    res = c.post(f"{PREFIX}/clients", json={"business_name": f"Denied {uuid.uuid4().hex[:6]}"})
    assert res.status_code == 403


@pytest.mark.parametrize("email", [DEVELOPER, DESIGNER])
def test_clients_id_routes_wrong_role_404(email: str):
    founder = _client()
    _login(founder, FOUNDER)
    created = founder.post(f"{PREFIX}/clients", json={"business_name": f"RoleGate {uuid.uuid4().hex[:6]}"})
    assert created.status_code == 201, created.text
    cid = created.json()["id"]

    c = _client()
    _login(c, email)
    assert c.get(f"{PREFIX}/clients/{cid}").status_code == 404
    assert c.patch(f"{PREFIX}/clients/{cid}", json={"business_name": "Nope"}).status_code == 404
    assert c.post(f"{PREFIX}/clients/{cid}/archive").status_code == 404
    missing = c.get(f"{PREFIX}/clients/{uuid.uuid4()}")
    assert missing.status_code == 404
    assert c.get(f"{PREFIX}/clients/{cid}").json() == missing.json()


# --- Invoices ---


@pytest.mark.parametrize("email", [DEVELOPER, DESIGNER, PM])
def test_invoice_post_non_founder_403(email: str):
    founder = _client()
    _login(founder, FOUNDER)
    cid = _founder_client_id(founder)

    c = _client()
    _login(c, email)
    res = c.post(
        f"{PREFIX}/invoices",
        json={"client_id": cid, "amount": "100.00", "status": "draft"},
    )
    assert res.status_code == 403, res.text


@pytest.mark.parametrize("email", [DEVELOPER, DESIGNER, PM])
def test_invoice_patch_non_founder_404(email: str):
    founder = _client()
    _login(founder, FOUNDER)
    cid = _founder_client_id(founder)
    created = founder.post(
        f"{PREFIX}/invoices",
        json={"client_id": cid, "amount": "250.00", "status": "draft"},
    )
    assert created.status_code == 201, created.text
    iid = created.json()["id"]

    c = _client()
    _login(c, email)
    res = c.patch(f"{PREFIX}/invoices/{iid}", json={"status": "sent"})
    assert res.status_code == 404, res.text
    missing = c.patch(f"{PREFIX}/invoices/{uuid.uuid4()}", json={"status": "sent"})
    assert missing.status_code == 404
    assert res.json() == missing.json()


# --- Projects & tasks ---


def test_project_post_developer_403():
    founder = _client()
    _login(founder, FOUNDER)
    cid = _founder_client_id(founder)

    rahul = _client()
    _login(rahul, DEVELOPER)
    res = rahul.post(
        f"{PREFIX}/projects",
        json={
            "name": f"Dev Create {uuid.uuid4().hex[:6]}",
            "client_id": cid,
            "project_type": "Website",
            "member_ids": [],
            "priority": "low",
        },
    )
    assert res.status_code == 403, res.text


@pytest.mark.parametrize("email", [DEVELOPER, DESIGNER])
def test_project_patch_archive_milestones_wrong_role_404(email: str):
    founder = _client()
    _login(founder, FOUNDER)
    # Include the wrong-role user as member so membership isn't the deny reason for PATCH role gate
    uid = _user_id(founder, email)
    project = _hidden_project(founder, member_ids=[uid])
    pid = project["id"]

    c = _client()
    _login(c, email)
    assert c.patch(f"{PREFIX}/projects/{pid}", json={"name": "Hacked"}).status_code == 404
    assert c.post(f"{PREFIX}/projects/{pid}/archive").status_code == 404
    assert c.post(
        f"{PREFIX}/projects/{pid}/milestones",
        json={"title": "Nope", "phase": "planning", "status": "todo"},
    ).status_code == 404


def test_task_get_non_member_404():
    founder = _client()
    _login(founder, FOUNDER)
    project = _hidden_project(founder, member_ids=[])
    task = founder.post(
        f"{PREFIX}/tasks",
        json={
            "title": f"Secret task {uuid.uuid4().hex[:6]}",
            "project_id": project["id"],
            "status": "todo",
            "priority": "low",
        },
    )
    assert task.status_code == 201, task.text
    tid = task.json()["id"]

    rahul = _client()
    _login(rahul, DEVELOPER)
    res = rahul.get(f"{PREFIX}/tasks/{tid}")
    assert res.status_code == 404
    missing = rahul.get(f"{PREFIX}/tasks/{uuid.uuid4()}")
    assert missing.status_code == 404
    assert res.json() == missing.json()


# --- People ---


@pytest.mark.parametrize("email", [DEVELOPER, DESIGNER, PM])
def test_post_employees_non_founder_403(email: str):
    c = _client()
    _login(c, email)
    res = c.post(
        f"{PREFIX}/employees",
        json={
            "email": f"nope-{uuid.uuid4().hex[:6]}@studiosunny.com",
            "first_name": "No",
            "last_name": "Pe",
            "role_key": "developer",
            "job_title": "X",
            "password": DEMO_PASSWORD,
        },
    )
    assert res.status_code == 403


def test_invite_developer_403():
    c = _client()
    _login(c, DEVELOPER)
    res = c.post(
        f"{PREFIX}/employees/invite",
        json={
            "email": f"invite-{uuid.uuid4().hex[:6]}@studiosunny.com",
            "first_name": "Inv",
            "last_name": "Itee",
            "role_key": "developer",
            "job_title": "Engineer",
        },
    )
    assert res.status_code == 403, res.text


@pytest.mark.parametrize("path", [f"{PREFIX}/employees/departments", f"{PREFIX}/employees/roles"])
def test_people_meta_401(path: str):
    assert _client().get(path).status_code == 401


# --- Chat ---


def test_chat_channels_401():
    assert _client().get(f"{PREFIX}/chat/channels").status_code == 401


def test_chat_non_member_messages_404():
    from sqlalchemy import select

    from app.core.tenant import STUDIO_SUNNY_ORG_ID
    from app.db.session import SessionLocal
    from app.models.chat import ChatChannel, ChatChannelMember
    from app.models.user import User

    slug = f"private-{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        sunny = db.scalar(select(User).where(User.email == FOUNDER))
        assert sunny
        ch = ChatChannel(
            slug=slug,
            name="Private Authz",
            topic="members only",
            kind="channel",
            org_id=STUDIO_SUNNY_ORG_ID,
        )
        db.add(ch)
        db.flush()
        db.add(ChatChannelMember(channel_id=ch.id, user_id=sunny.id, org_id=STUDIO_SUNNY_ORG_ID))
        db.commit()
    finally:
        db.close()

    rahul = _client()
    _login(rahul, DEVELOPER)
    res = rahul.get(f"{PREFIX}/chat/channels/{slug}/messages")
    assert res.status_code == 404
    post = rahul.post(f"{PREFIX}/chat/channels/{slug}/messages", json={"body": "intrude"})
    assert post.status_code == 404


def test_chat_message_author_patch_delete_and_other_404():
    sunny = _client()
    _login(sunny, FOUNDER)
    posted = sunny.post(f"{PREFIX}/chat/channels/general/messages", json={"body": f"authz-{uuid.uuid4().hex[:6]}"})
    assert posted.status_code == 201, posted.text
    mid = posted.json()["id"]

    ok = sunny.patch(f"{PREFIX}/chat/channels/general/messages/{mid}", json={"body": "edited by author"})
    assert ok.status_code == 200, ok.text

    rahul = _client()
    _login(rahul, DEVELOPER)
    deny = rahul.patch(f"{PREFIX}/chat/channels/general/messages/{mid}", json={"body": "stolen edit"})
    assert deny.status_code == 404
    deny_del = rahul.delete(f"{PREFIX}/chat/channels/general/messages/{mid}")
    assert deny_del.status_code == 404

    deleted = sunny.delete(f"{PREFIX}/chat/channels/general/messages/{mid}")
    assert deleted.status_code == 204


# --- Docs ---


def test_docs_list_401():
    assert _client().get(f"{PREFIX}/docs").status_code == 401


def test_docs_non_visible_get_patch_delete_yjs_404():
    sunny = _client()
    _login(sunny, FOUNDER)
    created = sunny.post(
        f"{PREFIX}/docs",
        json={
            "title": f"Private Doc {uuid.uuid4().hex[:6]}",
            "kind": "page",
            "content": {"type": "doc", "content": []},
        },
    )
    assert created.status_code == 201, created.text
    doc_id = created.json()["id"]

    rahul = _client()
    _login(rahul, DEVELOPER)
    get_r = rahul.get(f"{PREFIX}/docs/{doc_id}")
    assert get_r.status_code == 404
    assert rahul.patch(f"{PREFIX}/docs/{doc_id}", json={"title": "Nope"}).status_code == 404
    assert rahul.delete(f"{PREFIX}/docs/{doc_id}").status_code == 404
    assert rahul.get(f"{PREFIX}/docs/{doc_id}/yjs").status_code == 404
    missing = rahul.get(f"{PREFIX}/docs/{uuid.uuid4()}")
    assert missing.status_code == 404
    assert get_r.json() == missing.json()


# --- Files ---


def test_files_list_401():
    assert _client().get(f"{PREFIX}/files").status_code == 401


def test_files_get_download_non_owned_404():
    sunny = _client()
    _login(sunny, FOUNDER)
    uploaded = sunny.post(
        f"{PREFIX}/files",
        data={"name": f"Private asset {uuid.uuid4().hex[:6]}", "kind": "asset"},
        files={"file": ("private.txt", b"secret-bytes", "text/plain")},
    )
    assert uploaded.status_code == 201, uploaded.text
    fid = uploaded.json()["id"]

    rahul = _client()
    _login(rahul, DEVELOPER)
    get_r = rahul.get(f"{PREFIX}/files/{fid}")
    assert get_r.status_code == 404
    assert rahul.get(f"{PREFIX}/files/{fid}/download").status_code == 404
    missing = rahul.get(f"{PREFIX}/files/{uuid.uuid4()}")
    assert missing.status_code == 404
    assert get_r.json() == missing.json()


# --- Admin ---


@pytest.mark.parametrize(
    "method,path,json_body",
    [
        ("GET", f"{PREFIX}/admin/permissions", None),
        ("GET", f"{PREFIX}/admin/integrations", None),
        ("GET", f"{PREFIX}/admin/templates", None),
        ("POST", f"{PREFIX}/admin/templates", {"kind": "email", "title": "X", "body": {}}),
        ("GET", f"{PREFIX}/admin/settings", None),
        ("GET", f"{PREFIX}/audit", None),
    ],
)
def test_admin_surfaces_403_for_developer(method: str, path: str, json_body):
    c = _client()
    _login(c, DEVELOPER)
    if method == "GET":
        res = c.get(path)
    else:
        res = c.post(path, json=json_body or {})
    assert res.status_code == 403, f"{method} {path} → {res.status_code}"


def test_integrations_no_raw_secrets_for_founder():
    from app.core.config import settings

    c = _client()
    _login(c, FOUNDER)
    res = c.get(f"{PREFIX}/admin/integrations")
    assert res.status_code == 200, res.text
    body = res.text
    for secret in (
        settings.google_client_secret,
        settings.sentry_dsn,
        settings.posthog_api_key,
        settings.smtp_password,
    ):
        if secret:
            assert secret not in body
    # Shape should stay status-only (no obvious secret fields)
    for row in res.json():
        assert "configured" in row
        for key in ("api_key", "secret", "token", "password", "dsn"):
            assert key not in row


# --- Auth validation ---


def test_2fa_disable_without_password_422():
    c = _client()
    _login(c, FOUNDER)
    res = c.post(f"{PREFIX}/auth/2fa/disable", json={"code": "123456"})
    assert res.status_code == 422


# --- Comments ---


def test_comment_author_patch_own_other_404():
    founder = _client()
    _login(founder, FOUNDER)
    rahul_id = _user_id(founder, DEVELOPER)
    priya_id = _user_id(founder, DESIGNER)
    project = _hidden_project(founder, member_ids=[rahul_id, priya_id])
    task = founder.post(
        f"{PREFIX}/tasks",
        json={
            "title": f"Comment gate {uuid.uuid4().hex[:6]}",
            "project_id": project["id"],
            "status": "todo",
            "priority": "medium",
            "assignee_id": rahul_id,
        },
    )
    assert task.status_code == 201, task.text
    tid = task.json()["id"]

    rahul = _client()
    _login(rahul, DEVELOPER)
    created = rahul.post(f"{PREFIX}/tasks/{tid}/comments", json={"body": "mine"})
    assert created.status_code == 201, created.text
    cid = created.json()["id"]

    ok = rahul.patch(f"{PREFIX}/tasks/{tid}/comments/{cid}", json={"body": "edited by author"})
    assert ok.status_code == 200, ok.text
    assert ok.json()["body"] == "edited by author"

    priya = _client()
    _login(priya, DESIGNER)
    deny = priya.patch(f"{PREFIX}/tasks/{tid}/comments/{cid}", json={"body": "stolen"})
    assert deny.status_code == 404
    deny_del = priya.delete(f"{PREFIX}/tasks/{tid}/comments/{cid}")
    assert deny_del.status_code == 404
    missing = priya.patch(f"{PREFIX}/tasks/{tid}/comments/{uuid.uuid4()}", json={"body": "x"})
    assert missing.status_code == 404
    assert deny.json() == missing.json()


# --- Membership / IDOR ---


def test_project_non_member_404():
    """Find a project Rahul is not on; GET must 404 (not 403)."""
    founder = _client()
    _login(founder, FOUNDER)
    projects = founder.get(f"{PREFIX}/projects").json()

    rahul = _client()
    _login(rahul, DEVELOPER)
    visible = {p["id"] for p in rahul.get(f"{PREFIX}/projects").json()}

    hidden = next((p for p in projects if p["id"] not in visible), None)
    if not hidden:
        hidden = _hidden_project(founder, member_ids=[])

    res = rahul.get(f"{PREFIX}/projects/{hidden['id']}")
    assert res.status_code == 404, res.text
    missing = rahul.get(f"{PREFIX}/projects/{uuid.uuid4()}")
    assert missing.status_code == 404
    assert res.json() == missing.json()


def test_post_task_non_member_403():
    founder = _client()
    _login(founder, FOUNDER)
    project = _hidden_project(founder, member_ids=[])
    project_id = project["id"]

    rahul = _client()
    _login(rahul, DEVELOPER)
    res = rahul.post(
        f"{PREFIX}/tasks",
        json={"title": "Should fail", "project_id": project_id, "status": "todo", "priority": "medium"},
    )
    assert res.status_code == 403, res.text


def test_notification_foreign_id_404():
    sunny = _client()
    _login(sunny, FOUNDER)
    notes = sunny.get(f"{PREFIX}/notifications").json()
    if not notes:
        return
    nid = notes[0]["id"]

    rahul = _client()
    _login(rahul, DEVELOPER)
    res = rahul.post(f"{PREFIX}/notifications/{nid}/read")
    assert res.status_code == 404


# --- Search isolation ---


def test_search_isolation_nonce():
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.client import Client
    from app.models.document import Document
    from app.models.file_asset import FileAsset
    from app.models.lead import Lead
    from app.models.task import Task
    from app.core.tenant import STUDIO_SUNNY_ORG_ID

    nonce = "ZZQX7"
    db = SessionLocal()
    try:
        c = Client(
            business_name=f"Secret {nonce} Client",
            slug=f"secret-{nonce.lower()}-{uuid.uuid4().hex[:4]}",
            status="active",
            org_id=STUDIO_SUNNY_ORG_ID,
        )
        db.add(c)
        db.flush()
        lead = Lead(
            business_name=f"Secret {nonce} Lead",
            stage="new_lead",
            org_id=STUDIO_SUNNY_ORG_ID,
        )
        db.add(lead)
        # Task on a project Rahul is not on — attach to first project without him if possible
        from app.models.project import Project
        from app.models.user import User

        sunny_id = db.scalar(select(User.id).where(User.email == FOUNDER))
        # Dedicated empty project — never rely on "first project Rahul isn't on"
        # (hostile seed may put designers on projects developers aren't).
        isolated = Project(
            name=f"Isolated {nonce}",
            slug=f"isolated-{nonce.lower()}-{uuid.uuid4().hex[:6]}",
            client_id=c.id,
            status="active",
            project_type="Website",
            org_id=STUDIO_SUNNY_ORG_ID,
        )
        db.add(isolated)
        db.flush()
        db.add(
            Task(
                title=f"Secret {nonce} Task",
                project_id=isolated.id,
                status="todo",
                priority="low",
                org_id=STUDIO_SUNNY_ORG_ID,
                created_by_id=sunny_id,
            )
        )
        db.add(
            Document(
                title=f"Secret {nonce} Doc",
                slug=f"secret-doc-{nonce.lower()}-{uuid.uuid4().hex[:4]}",
                kind="page",
                content={"type": "doc", "content": []},
                org_id=STUDIO_SUNNY_ORG_ID,
                created_by_id=sunny_id,
            )
        )
        db.add(
            FileAsset(
                name=f"secret-{nonce}.txt",
                original_name=f"secret-{nonce}.txt",
                storage_key=f"test/{nonce}-{uuid.uuid4().hex}",
                mime_type="text/plain",
                size_bytes=12,
                org_id=STUDIO_SUNNY_ORG_ID,
                uploaded_by_id=sunny_id,
            )
        )
        db.commit()
    finally:
        db.close()

    for email in (DEVELOPER, DESIGNER):
        c = _client()
        _login(c, email)
        res = c.get(f"{PREFIX}/search", params={"q": nonce})
        assert res.status_code == 200, res.text
        assert nonce not in res.text, f"{email} saw nonce in search: {res.text[:500]}"


# --- Override escalation ---


def test_permission_override_cannot_grant_founder_surfaces():
    founder = _client()
    _login(founder, FOUNDER)
    # Attempt to grant finance/audit/admin to developer
    res = founder.put(
        f"{PREFIX}/admin/permissions/overrides",
        json={
            "overrides": {
                "developer": ["finance:read", "audit:read", "reports:read", "settings:write"],
            }
        },
    )
    assert res.status_code in (200, 400, 422), res.text

    rahul = _client()
    _login(rahul, DEVELOPER)
    assert rahul.get(f"{PREFIX}/audit").status_code == 403
    assert rahul.get(f"{PREFIX}/invoices").status_code == 403
    assert rahul.get(f"{PREFIX}/reports").status_code == 403
    assert rahul.get(f"{PREFIX}/admin/settings").status_code == 403


# --- Gaps: archive / deactivate ---


def test_archive_client_founder_pm_only():
    founder = _client()
    _login(founder, FOUNDER)
    created = founder.post(f"{PREFIX}/clients", json={"business_name": f"Archive Me {uuid.uuid4().hex[:6]}"})
    assert created.status_code == 201, created.text
    cid = created.json()["id"]

    rahul = _client()
    _login(rahul, DEVELOPER)
    deny = rahul.post(f"{PREFIX}/clients/{cid}/archive")
    assert deny.status_code in (403, 404)

    ok = founder.post(f"{PREFIX}/clients/{cid}/archive")
    assert ok.status_code == 204
    # Soft-archive: detail stays readable for Archived filter / deep links
    got = founder.get(f"{PREFIX}/clients/{cid}")
    assert got.status_code == 200
    assert got.json().get("archived") is True
    active = founder.get(f"{PREFIX}/clients").json()
    assert all(c["id"] != cid for c in active)
    archived = founder.get(f"{PREFIX}/clients", params={"archived": "true"}).json()
    assert any(c["id"] == cid for c in archived)


def test_deactivate_employee_founder_only_revokes_sessions():
    founder = _client()
    _login(founder, FOUNDER)
    email = f"offboard-{uuid.uuid4().hex[:8]}@studiosunny.com"
    created = founder.post(
        f"{PREFIX}/employees",
        json={
            "email": email,
            "first_name": "Off",
            "last_name": "Board",
            "role_key": "developer",
            "job_title": "Contractor",
            "password": DEMO_PASSWORD,
        },
    )
    assert created.status_code == 201, created.text
    emp_id = created.json()["id"]

    victim = _client()
    _login(victim, email)
    assert victim.get(f"{PREFIX}/auth/me").status_code == 200

    rahul = _client()
    _login(rahul, DEVELOPER)
    assert rahul.delete(f"{PREFIX}/employees/{emp_id}").status_code == 403

    res = founder.delete(f"{PREFIX}/employees/{emp_id}")
    assert res.status_code == 204

    refresh = victim.post(f"{PREFIX}/auth/refresh")
    assert refresh.status_code in (401, 403)


def test_mass_assignment_ignored_on_client_create():
    c = _client()
    _login(c, FOUNDER)
    forged_id = str(uuid.uuid4())
    res = c.post(
        f"{PREFIX}/clients",
        json={
            "business_name": f"Mass Assign {uuid.uuid4().hex[:6]}",
            "id": forged_id,
            "org_id": str(uuid.uuid4()),
            "created_at": "2000-01-01T00:00:00Z",
            "is_active": False,
            "owner_id": forged_id,
            "role": "founder",
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["id"] != forged_id
    assert body.get("business_name", "").startswith("Mass Assign")


# --- Extra role-matrix sweeps (parametric) ---


@pytest.mark.parametrize(
    "email,path,expected",
    [
        (DEVELOPER, f"{PREFIX}/clients", 403),
        (DEVELOPER, f"{PREFIX}/leads", 403),
        (DEVELOPER, f"{PREFIX}/invoices", 403),
        (DEVELOPER, f"{PREFIX}/reports", 403),
        (DEVELOPER, f"{PREFIX}/audit", 403),
        (DESIGNER, f"{PREFIX}/clients", 403),
        (DESIGNER, f"{PREFIX}/invoices", 403),
        (PM, f"{PREFIX}/clients", 200),
        (PM, f"{PREFIX}/leads", 200),
        (PM, f"{PREFIX}/invoices", 403),
        (PM, f"{PREFIX}/audit", 403),
        (FOUNDER, f"{PREFIX}/invoices", 200),
        (FOUNDER, f"{PREFIX}/audit", 200),
        (FOUNDER, f"{PREFIX}/admin/integrations", 200),
        (FOUNDER, f"{PREFIX}/admin/permissions", 200),
        (PM, f"{PREFIX}/admin/templates", 200),
        (DEVELOPER, f"{PREFIX}/admin/templates", 403),
    ],
)
def test_role_gated_collections(email: str, path: str, expected: int):
    c = _client()
    _login(c, email)
    assert c.get(path).status_code == expected


@pytest.mark.parametrize("email", [DEVELOPER, DESIGNER, PM, FOUNDER])
def test_authenticated_workspace_ok(email: str):
    c = _client()
    _login(c, email)
    for path in (
        f"{PREFIX}/desk",
        f"{PREFIX}/calendar/events",
        f"{PREFIX}/activity",
        f"{PREFIX}/notifications",
        f"{PREFIX}/ai/briefing",
        f"{PREFIX}/chat/channels",
        f"{PREFIX}/docs",
        f"{PREFIX}/files",
        f"{PREFIX}/employees/departments",
        f"{PREFIX}/employees/roles",
        f"{PREFIX}/auth/sessions",
    ):
        res = c.get(path)
        assert res.status_code == 200, f"{email} {path} → {res.status_code}"


# --- Hardening: client IP, WebSockets, chat delete fan-out ---


def test_xff_rate_limit_buckets_are_independent(monkeypatch):
    """Two X-Forwarded-For values (behind trusted proxy) must not share a login IP bucket."""
    from app.core.config import settings
    from app.core.rate_limit import LOGIN_IP_LIMIT, login_ip_limiter

    monkeypatch.setattr(settings, "trusted_proxy_ips", "127.0.0.1,::1,testclient")
    login_ip_limiter.reset("login:ip:203.0.113.10")
    login_ip_limiter.reset("login:ip:203.0.113.20")

    def fail_login(xff: str, email: str):
        c = _client()
        return c.post(
            f"{PREFIX}/auth/login",
            json={"email": email, "password": "definitely-wrong-password"},
            headers={"X-Forwarded-For": xff},
        )

    for i in range(LOGIN_IP_LIMIT + 2):
        fail_login("203.0.113.10", f"xff-a-{i}-{uuid.uuid4().hex[:6]}@studiosunny.com")
    blocked = fail_login("203.0.113.10", f"xff-blocked-{uuid.uuid4().hex[:6]}@studiosunny.com")
    assert blocked.status_code == 429

    other = fail_login("203.0.113.20", f"xff-ok-{uuid.uuid4().hex[:6]}@studiosunny.com")
    assert other.status_code == 401


def test_chat_ws_rejects_unauthenticated():
    c = _client()
    with pytest.raises(Exception):
        with c.websocket_connect(f"{PREFIX}/chat/ws") as ws:
            ws.send_json({"type": "ping"})
            ws.receive_json()


def test_chat_ws_subscribe_non_member_channel():
    from sqlalchemy import select

    from app.core.tenant import STUDIO_SUNNY_ORG_ID
    from app.db.session import SessionLocal
    from app.models.chat import ChatChannel, ChatChannelMember
    from app.models.user import User

    db = SessionLocal()
    try:
        slug = f"authz-private-{uuid.uuid4().hex[:6]}"
        ch = ChatChannel(slug=slug, name="Private", kind="channel", org_id=STUDIO_SUNNY_ORG_ID)
        db.add(ch)
        db.flush()
        sunny_u = db.scalar(select(User).where(User.email == FOUNDER))
        db.add(ChatChannelMember(channel_id=ch.id, user_id=sunny_u.id, org_id=STUDIO_SUNNY_ORG_ID))
        db.commit()
    finally:
        db.close()

    rahul = _client()
    _login(rahul, DEVELOPER)
    with rahul.websocket_connect(f"{PREFIX}/chat/ws") as ws:
        ws.send_json({"type": "subscribe", "channel": slug})
        msg = ws.receive_json()
        assert msg.get("type") == "error"
        assert msg.get("code") == 4403


def test_docs_collab_ws_rejects_non_writer():
    founder = _client()
    _login(founder, FOUNDER)
    created = founder.post(
        f"{PREFIX}/docs",
        json={
            "title": f"WS Collab {uuid.uuid4().hex[:6]}",
            "kind": "page",
            "content": {"type": "doc", "content": []},
        },
    )
    assert created.status_code == 201, created.text
    doc_id = created.json()["id"]

    rahul = _client()
    _login(rahul, DEVELOPER)
    with pytest.raises(Exception):
        with rahul.websocket_connect(f"{PREFIX}/docs/{doc_id}/collab") as ws:
            ws.receive_json()


def test_chat_message_delete_broadcasts_over_ws():
    sunny = _client()
    _login(sunny, FOUNDER)
    watcher = _client()
    _login(watcher, FOUNDER)
    with watcher.websocket_connect(f"{PREFIX}/chat/ws") as ws:
        ws.send_json({"type": "subscribe", "channel": "general"})
        # drain presence (and any stray events)
        for _ in range(3):
            try:
                evt = ws.receive_json()
                if evt.get("type") == "presence":
                    break
            except Exception:
                break

        mid_res = sunny.post(
            f"{PREFIX}/chat/channels/general/messages",
            json={"body": f"retract-live-{uuid.uuid4().hex[:6]}"},
        )
        assert mid_res.status_code == 201, mid_res.text
        mid = mid_res.json()["id"]

        got_new = False
        got_del = False
        for _ in range(12):
            evt = ws.receive_json()
            if evt.get("type") == "message" and (evt.get("message") or {}).get("id") == mid:
                got_new = True
                del_res = sunny.delete(f"{PREFIX}/chat/channels/general/messages/{mid}")
                assert del_res.status_code == 204
            if evt.get("type") == "message_deleted" and evt.get("message_id") == mid:
                got_del = True
                break
        assert got_new, "live client never saw the new message"
        assert got_del, "DELETE did not fan out message_deleted over the socket"
