"""Migration safety suite (Postgres).

Prefers MIGRATION_DATABASE_URL / non-sqlite DATABASE_URL (CI service container),
else testcontainers when Docker is up. Skip cleanly when neither is available.
"""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ROOT / "alembic" / "versions"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "prod_shape.sql"
ALEMBIC_INI = ROOT / "alembic.ini"

pytestmark = pytest.mark.migrations


def _normalize_pg_url(url: str) -> str:
    url = url.replace("psycopg2", "psycopg")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _env_pg_url() -> str | None:
    for key in ("MIGRATION_DATABASE_URL", "DATABASE_URL"):
        raw = os.environ.get(key, "").strip()
        if raw.startswith("postgresql"):
            return _normalize_pg_url(raw)
    return None


def _in_ci() -> bool:
    return os.environ.get("CI", "").lower() in {"1", "true", "yes"}


def _docker_ok() -> bool:
    try:
        pytest.importorskip("testcontainers")
        from testcontainers.core.docker_client import DockerClient

        DockerClient().client.ping()
        return True
    except Exception:
        return False


def _pg_available() -> bool:
    # In CI we never "skip available" — missing Postgres must fail the job.
    if _in_ci() or _env_pg_url():
        return True
    return _docker_ok()


requires_pg = pytest.mark.skipif(
    not _pg_available(),
    reason="No MIGRATION_DATABASE_URL and Docker unavailable for testcontainers",
)


def _assert_reachable(url: str) -> None:
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.fail(f"Postgres unreachable for migration tests ({exc})")


@pytest.fixture(scope="module")
def pg_url():
    env = _env_pg_url()
    if env:
        _assert_reachable(env)
        yield env
        return
    if _in_ci():
        # Trap: a miswired services: block must not become another skip.
        pytest.fail(
            "CI requires a reachable MIGRATION_DATABASE_URL (or working Docker for "
            "testcontainers); refusing to skip migration data tests"
        )
    if not _docker_ok():
        pytest.skip("No MIGRATION_DATABASE_URL and Docker unavailable for testcontainers")
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine") as pg:
        url = _normalize_pg_url(pg.get_connection_url())
        _assert_reachable(url)
        yield url


def _alembic_cfg(url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    # Ensure env.py picks up this URL
    os.environ["DATABASE_URL"] = url
    return cfg


def _table_counts(engine) -> dict[str, int]:
    insp = inspect(engine)
    counts: dict[str, int] = {}
    with engine.connect() as conn:
        for name in insp.get_table_names():
            if name == "alembic_version":
                continue
            counts[name] = int(conn.execute(text(f'SELECT COUNT(*) FROM "{name}"')).scalar() or 0)
    return counts


def _null_nonnull_snapshot(engine) -> dict[tuple[str, str], int]:
    """Count non-null values per column (for columns that had any non-null data)."""
    insp = inspect(engine)
    snap: dict[tuple[str, str], int] = {}
    with engine.connect() as conn:
        for table in insp.get_table_names():
            if table == "alembic_version":
                continue
            for col in insp.get_columns(table):
                cname = col["name"]
                n = int(
                    conn.execute(
                        text(f'SELECT COUNT(*) FROM "{table}" WHERE "{cname}" IS NOT NULL')
                    ).scalar()
                    or 0
                )
                if n > 0:
                    snap[(table, cname)] = n
    return snap


def test_linear_migration_history():
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    script = ScriptDirectory.from_config(cfg)
    downs: dict[str | None, list[str]] = {}
    for rev in script.walk_revisions():
        key = rev.down_revision
        if isinstance(key, (list, tuple)):
            for k in key:
                downs.setdefault(k, []).append(rev.revision)
        else:
            downs.setdefault(key, []).append(rev.revision)
    branched = {k: v for k, v in downs.items() if len(v) > 1}
    assert not branched, f"Branched Alembic history (shared down_revision): {branched}"


def test_destructive_operation_guard():
    """Fail on drop_table / drop_column / typed alter_column without review comment."""
    pattern_drop = re.compile(r"\b(drop_table|drop_column)\b")
    pattern_alter_type = re.compile(r"alter_column\([^)]*type_?", re.IGNORECASE | re.DOTALL)
    review = re.compile(r"#\s*reviewed-destructive:\s*\S+")
    offenders: list[str] = []
    for path in sorted(VERSIONS.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if not (pattern_drop.search(text) or pattern_alter_type.search(text)):
            continue
        if not review.search(text):
            offenders.append(path.name)
    assert not offenders, (
        "Destructive ops require `# reviewed-destructive: <reason>` in: " + ", ".join(offenders)
    )


def test_every_migration_has_real_downgrade():
    for path in sorted(VERSIONS.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        fn = next(
            (
                n
                for n in tree.body
                if isinstance(n, ast.FunctionDef) and n.name == "downgrade"
            ),
            None,
        )
        assert fn is not None, f"{path.name}: missing downgrade()"
        body = list(fn.body)
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(getattr(body[0], "value", None), ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            body = body[1:]
        assert body, f"{path.name}: downgrade() is empty"
        for node in body:
            if isinstance(node, ast.Pass):
                pytest.fail(f"{path.name}: downgrade() is only `pass`")
            if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
                if isinstance(node.exc.func, ast.Name) and node.exc.func.id == "NotImplementedError":
                    pytest.fail(f"{path.name}: downgrade() raises NotImplementedError")
            if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Name):
                if node.exc.id == "NotImplementedError":
                    pytest.fail(f"{path.name}: downgrade() raises NotImplementedError")


@requires_pg
def test_round_trip_upgrade_downgrade_upgrade(pg_url):
    cfg = _alembic_cfg(pg_url)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    engine = create_engine(pg_url)
    with engine.connect() as conn:
        ver = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert ver is not None


@requires_pg
def test_model_drift_autogenerate_empty(pg_url):
    from alembic.autogenerate import compare_metadata
    from alembic.runtime.migration import MigrationContext

    from app.db.base import Base
    from app import models  # noqa: F401

    cfg = _alembic_cfg(pg_url)
    command.upgrade(cfg, "head")
    engine = create_engine(pg_url)
    with engine.connect() as conn:
        mc = MigrationContext.configure(conn, opts={"compare_type": True})
        diff = compare_metadata(mc, Base.metadata)
    assert diff == [], f"Model/metadata drift vs migrations:\n{diff!r}"


@requires_pg
def test_upgrade_over_prod_shape_preserves_rows(pg_url):
    assert FIXTURE.exists(), f"Missing {FIXTURE}"
    cfg = _alembic_cfg(pg_url)
    command.upgrade(cfg, "0001_initial")
    engine = create_engine(pg_url)
    sql = FIXTURE.read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.execute(text(sql))
    before_counts = _table_counts(engine)
    before_nonnull = _null_nonnull_snapshot(engine)
    assert before_counts.get("users", 0) >= 1
    assert before_counts.get("tasks", 0) >= 1

    command.upgrade(cfg, "head")

    after_counts = _table_counts(engine)
    after_nonnull = _null_nonnull_snapshot(engine)
    for table, n in before_counts.items():
        assert after_counts.get(table, 0) == n, f"{table} row count changed {n} → {after_counts.get(table)}"
    for key, n in before_nonnull.items():
        table, col = key
        assert after_nonnull.get(key, 0) == n, (
            f"{table}.{col} lost non-null values ({n} → {after_nonnull.get(key, 0)})"
        )
