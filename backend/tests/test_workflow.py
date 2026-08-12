from fastapi.testclient import TestClient

from app.main import app
from app.seed.seed import DEMO_PASSWORD, run as seed_run

seed_run()
client = TestClient(app)


def _login(email: str, password: str = DEMO_PASSWORD):
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    csrf = res.json().get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    return res


def test_org_id_and_audit_trail():
    login = _login("sunny@studiosunny.com")
    assert login.json()["user"].get("org_id")
    created = client.post("/api/v1/clients", json={"business_name": "Audit Trail Co"})
    assert created.status_code == 201, created.text
    logs = client.get("/api/v1/audit")
    assert logs.status_code == 200, logs.text
    rows = logs.json()
    actions = [row["action"] for row in rows]
    assert any(a.startswith("auth.login") for a in actions)
    assert "client.create" in actions
    assert any(row.get("user_name") for row in rows)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_founder_workflow():
    login = _login("sunny@studiosunny.com")
    assert login.json()["user"]["role_key"] == "founder"
    assert login.json().get("csrf_token")

    dash = client.get("/api/v1/dashboard")
    assert dash.status_code == 200
    assert dash.json()["greeting_name"] == "Sunny"

    created_client = client.post(
        "/api/v1/clients",
        json={
            "business_name": "Harbor Lights Studio",
            "primary_contact_name": "Leela Nair",
            "email": "leela@harborlights.in",
            "industry": "Hospitality",
            "location": "Kochi",
        },
    )
    assert created_client.status_code == 201, created_client.text
    client_id = created_client.json()["id"]

    people = client.get("/api/v1/employees").json()
    arjun = next(p for p in people if p["email"] == "arjun@studiosunny.com")
    rahul = next(p for p in people if p["email"] == "rahul@studiosunny.com")

    project = client.post(
        "/api/v1/projects",
        json={
            "name": "Harbor Lights Booking Site",
            "client_id": client_id,
            "project_type": "Website",
            "project_manager_id": arjun["user_id"],
            "member_ids": [arjun["user_id"], rahul["user_id"]],
            "priority": "high",
        },
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    milestone = client.post(
        f"/api/v1/projects/{project_id}/milestones",
        json={"title": "Kickoff", "phase": "planning", "status": "in_progress"},
    )
    assert milestone.status_code == 201

    task = client.post(
        "/api/v1/tasks",
        json={
            "title": "Draft information architecture",
            "project_id": project_id,
            "assignee_id": rahul["user_id"],
            "priority": "high",
            "status": "todo",
        },
    )
    assert task.status_code == 201, task.text
    task_id = task.json()["id"]

    rahul_login = _login("rahul@studiosunny.com")
    assert rahul_login.status_code == 200
    desk = client.get("/api/v1/desk").json()
    assert any(t["id"] == task_id for t in desk["focus"] + desk["due_today"] + desk.get("upcoming", [])) or any(
        t["title"] == "Draft information architecture" for t in desk["focus"]
    )

    updated = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "in_progress"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"

    notes = client.get("/api/v1/notifications").json()
    assert isinstance(notes, list)

    ai = client.post("/api/v1/ai/ask", json={"question": "What is Rahul's salary?"})
    assert ai.status_code == 200
    assert (
        "can’t share compensation" in ai.json()["answer"].lower()
        or "can't share compensation" in ai.json()["answer"].lower()
        or "cannot" in ai.json()["answer"].lower()
        or "can’t" in ai.json()["answer"].lower()
    )


def test_finance_restricted_for_developer():
    _login("rahul@studiosunny.com")
    res = client.get("/api/v1/invoices")
    assert res.status_code == 403


def test_csrf_rejects_mutating_without_header():
    _login("sunny@studiosunny.com")
    client.headers.pop("X-CSRF-Token", None)
    res = client.post("/api/v1/clients", json={"business_name": "No CSRF Co"})
    assert res.status_code == 403


def test_refresh_rotation_and_chat():
    isolated = TestClient(app)
    login = isolated.post(
        "/api/v1/auth/login",
        json={"email": "sunny@studiosunny.com", "password": DEMO_PASSWORD},
    )
    assert login.status_code == 200
    csrf = login.json()["csrf_token"]
    old_refresh = login.cookies.get("ss_refresh")
    isolated.headers["X-CSRF-Token"] = csrf

    rotated = isolated.post("/api/v1/auth/refresh")
    assert rotated.status_code == 200, rotated.text
    if rotated.json().get("csrf_token"):
        isolated.headers["X-CSRF-Token"] = rotated.json()["csrf_token"]

    attacker = TestClient(app)
    attacker.cookies.set("ss_csrf", csrf)
    attacker.cookies.set("ss_refresh", old_refresh)
    attacker.headers["X-CSRF-Token"] = csrf
    reuse = attacker.post("/api/v1/auth/refresh")
    assert reuse.status_code == 401

    _login("sunny@studiosunny.com")
    channels = client.get("/api/v1/chat/channels")
    assert channels.status_code == 200
    slugs = [c["slug"] for c in channels.json()]
    assert "general" in slugs
    posted = client.post("/api/v1/chat/channels/general/messages", json={"body": "Ship the briefing."})
    assert posted.status_code == 201, posted.text
    history = client.get("/api/v1/chat/channels/general/messages")
    assert history.status_code == 200
    assert any(m["body"] == "Ship the briefing." for m in history.json())


def test_docs_crud():
    _login("sunny@studiosunny.com")
    listed = client.get("/api/v1/docs")
    assert listed.status_code == 200, listed.text
    assert isinstance(listed.json(), list)

    created = client.post(
        "/api/v1/docs",
        json={
            "title": "Sprint notes",
            "kind": "page",
            "content": {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Ship docs this week."}],
                    }
                ],
            },
        },
    )
    assert created.status_code == 201, created.text
    doc_id = created.json()["id"]
    assert created.json()["title"] == "Sprint notes"

    updated = client.patch(
        f"/api/v1/docs/{doc_id}",
        json={"title": "Sprint notes — final", "status": "published"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["title"] == "Sprint notes — final"
    assert updated.json()["status"] == "published"

    fetched = client.get(f"/api/v1/docs/{doc_id}")
    assert fetched.status_code == 200
    assert "Ship docs" in (fetched.json().get("plain_text") or "")

    deleted = client.delete(f"/api/v1/docs/{doc_id}")
    assert deleted.status_code == 204
    missing = client.get(f"/api/v1/docs/{doc_id}")
    assert missing.status_code == 404


def test_files_upload_download():
    _login("sunny@studiosunny.com")
    listed = client.get("/api/v1/files")
    assert listed.status_code == 200, listed.text

    uploaded = client.post(
        "/api/v1/files",
        data={"name": "Launch checklist", "kind": "asset"},
        files={"file": ("launch-checklist.txt", b"Checkout QA items\n", "text/plain")},
    )
    assert uploaded.status_code == 201, uploaded.text
    file_id = uploaded.json()["id"]
    assert uploaded.json()["name"] == "Launch checklist"
    assert uploaded.json()["size_bytes"] > 0

    meta = client.get(f"/api/v1/files/{file_id}")
    assert meta.status_code == 200

    download = client.get(f"/api/v1/files/{file_id}/download")
    assert download.status_code == 200
    assert b"Checkout QA" in download.content

    deleted = client.delete(f"/api/v1/files/{file_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/files/{file_id}").status_code == 404

    # Freelancer cannot write credentials; developer without credentials can't list vault
    _login("rahul@studiosunny.com")
    denied = client.post(
        "/api/v1/files",
        data={"name": "Secret", "kind": "credential"},
        files={"file": ("secret.txt", b"x", "text/plain")},
    )
    assert denied.status_code == 403


def test_calendar_events():
    _login("sunny@studiosunny.com")
    res = client.get("/api/v1/calendar/events")
    assert res.status_code == 200, res.text
    assert isinstance(res.json(), list)
    for row in res.json():
        assert "date" in row and "kind" in row and "title" in row


def test_auth_providers_and_2fa_setup():
    providers = client.get("/api/v1/auth/providers")
    assert providers.status_code == 200
    assert "google" in providers.json()

    _login("sunny@studiosunny.com")
    setup = client.post("/api/v1/auth/2fa/setup")
    assert setup.status_code == 200, setup.text
    assert setup.json()["secret"]
    assert setup.json()["otpauth_url"].startswith("otpauth://")


def test_worker_settings_importable():
    from app.worker import WorkerSettings, daily_digest

    assert WorkerSettings.functions
    assert daily_digest

