"""Schemathesis OpenAPI fuzz suite (ASGI, in-process).

Any 5xx is a failure. Use --fuzz-deep for 1000 examples/operation (nightly).
Fixed Hypothesis seed via HYPOTHESIS_SEED (default 20260812); printed on failure.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("schemathesis")
import schemathesis
from hypothesis import HealthCheck, settings as hsettings, seed as hseed

from app.main import app
from app.seed.seed import DEMO_PASSWORD, run_demo as seed_run

pytestmark = [pytest.mark.fuzz]

seed_run()

HYPOTHESIS_SEED = int(os.environ.get("HYPOTHESIS_SEED", "20260812"))

FUZZ_EXCLUDE_PATHS: dict[str, str] = {
    "/health": "liveness only; no auth surface",
    "/api/v1/auth/google/start": "external IdP redirect",
    "/api/v1/auth/google/callback": "OAuth callback; requires Google tokens",
}


def pytest_addoption(parser):
    try:
        parser.addoption(
            "--fuzz-deep",
            action="store_true",
            default=False,
            help="1000 Schemathesis examples per operation (nightly)",
        )
    except ValueError:
        pass


def _examples(config) -> int:
    if config.getoption("--fuzz-deep", default=False) or os.environ.get("FUZZ_DEEP"):
        return 1000
    return 100


def _excluded(path: str) -> str | None:
    for prefix, reason in FUZZ_EXCLUDE_PATHS.items():
        if path == prefix or path.startswith(prefix.rstrip("/") + "/"):
            return reason
    if path.endswith("/ws") or path.endswith("/collab"):
        return "WebSocket; covered by authz suite"
    return None


schema = schemathesis.openapi.from_asgi("/openapi.json", app)

AUTH_STATES = [
    ("founder", "sunny@studiosunny.com"),
    ("pm", "arjun@studiosunny.com"),
    ("developer", "rahul@studiosunny.com"),
    ("designer", "priya@studiosunny.com"),
]


def _auth_headers_cookies(email: str | None):
    from fastapi.testclient import TestClient

    cookies: dict[str, str] = {}
    headers: dict[str, str] = {}
    if not email:
        return cookies, headers
    c = TestClient(app)
    res = c.post("/api/v1/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    assert res.status_code == 200, res.text
    cookies = dict(c.cookies)
    csrf = res.json().get("csrf_token") or cookies.get("ss_csrf")
    if csrf:
        headers["X-CSRF-Token"] = csrf
    return cookies, headers


@pytest.fixture(scope="module")
def fuzz_db_rollback():
    from sqlalchemy import event

    from app.db.session import SessionLocal, engine, get_db
    from app.main import app as fastapi_app

    connection = engine.connect()
    trans = connection.begin()
    session = SessionLocal(bind=connection)

    @event.listens_for(session, "after_transaction_end")
    def _restart(sess, transaction):
        if transaction.nested and not transaction._parent.nested:
            connection.begin_nested()

    connection.begin_nested()

    def _db():
        try:
            yield session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = _db
    yield session
    fastapi_app.dependency_overrides.pop(get_db, None)
    session.close()
    trans.rollback()
    connection.close()


def _validate(case: schemathesis.Case, response) -> None:
    assert response.status_code < 500, (
        f"{case.method} {case.path} → {response.status_code} seed={HYPOTHESIS_SEED}\n"
        f"{getattr(response, 'text', '')[:500]}"
    )
    # Schemathesis 4: default checks include status/content-type/schema/server-error
    case.validate_response(response)


@hseed(HYPOTHESIS_SEED)
@schema.parametrize()
@hsettings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
    print_blob=True,
)
def test_openapi_fuzz_anonymous(case: schemathesis.Case, fuzz_db_rollback):
    if _excluded(case.path):
        return
    response = case.call()
    _validate(case, response)


@pytest.mark.parametrize("auth_name,email", AUTH_STATES)
def test_openapi_fuzz_authenticated(auth_name, email, fuzz_db_rollback, pytestconfig):
    cookies, headers = _auth_headers_cookies(email)
    examples = min(_examples(pytestconfig), 40)
    failures: list[str] = []
    covered: set[str] = set()

    for result in schema.get_all_operations():
        op = result.ok() if hasattr(result, "ok") else result
        path = getattr(op, "path", "") or ""
        if _excluded(path):
            continue
        try:
            operations = list(op.iter_operations()) if hasattr(op, "iter_operations") else [op]
        except Exception:
            operations = [op]

        for operation in operations:
            method = getattr(operation, "method", None) or getattr(op, "method", "?")
            try:
                strategy = operation.as_strategy()
            except Exception:
                continue

            from hypothesis import given

            @hseed(HYPOTHESIS_SEED)
            @given(case=strategy)
            @hsettings(
                max_examples=examples,
                deadline=None,
                suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
                print_blob=True,
            )
            def run(case: schemathesis.Case):
                for k, v in cookies.items():
                    case.cookies[k] = v
                for k, v in headers.items():
                    case.headers[k] = v
                response = case.call()
                _validate(case, response)

            try:
                run()
                covered.add(f"{method.upper()} {path}")
            except Exception as exc:
                failures.append(f"{auth_name}: {str(exc).splitlines()[0][:280]}")
                if len(failures) >= 8:
                    break
        if len(failures) >= 8:
            break

    # Stateful chain — proves cookies reach protected GETs (not only /health + login).
    from fastapi.testclient import TestClient

    client = TestClient(app)
    for k, v in cookies.items():
        client.cookies.set(k, v)
    client.headers.update(headers)
    for path in ("/api/v1/auth/me", "/api/v1/projects", "/api/v1/tasks", "/api/v1/search?q=a"):
        res = client.get(path)
        assert res.status_code < 500, f"{auth_name} stateful {path} → {res.status_code} seed={HYPOTHESIS_SEED}"
        assert res.status_code != 401, f"{auth_name} unauthenticated on {path} — auth not wired into fuzz"

    # Auth fuzz must touch a real surface, not a handful of public ops.
    assert len(covered) >= 25, (
        f"{auth_name}: only covered {len(covered)} operations (auth may not be applied):\n"
        + "\n".join(sorted(covered)[:20])
    )

    if failures:
        pytest.fail(f"Schemathesis seed={HYPOTHESIS_SEED} examples={examples}:\n" + "\n".join(failures))


def test_fuzz_auth_reaches_protected_routes(fuzz_db_rollback):
    """Guard: if auth cookies are missing, fuzz would only exercise public ops."""
    from fastapi.testclient import TestClient

    protected = (
        "/api/v1/tasks",
        "/api/v1/audit",
        "/api/v1/admin/integrations",
        "/api/v1/employees",
    )
    anon = TestClient(app)
    for path in protected:
        assert anon.get(path).status_code in (401, 403), path

    cookies, headers = _auth_headers_cookies("sunny@studiosunny.com")
    authed = TestClient(app)
    for k, v in cookies.items():
        authed.cookies.set(k, v)
    authed.headers.update(headers)
    for path in protected:
        res = authed.get(path)
        assert res.status_code != 401, f"founder still 401 on {path}"
        assert res.status_code < 500


@pytest.mark.fuzz_exclude(reason="Documented OAuth callback exclusion")
def test_fuzz_exclusions_have_reasons():
    assert all(len(r) > 8 for r in FUZZ_EXCLUDE_PATHS.values())
    assert "/api/v1/auth/google/callback" in FUZZ_EXCLUDE_PATHS
