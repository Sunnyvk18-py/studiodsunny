#!/usr/bin/env python3
"""Generate a scrubbed prod-shaped SQL fixture (no real PII).

Creates schema + representative rows, then runs scrub_dump.py semantics
inline so tests/fixtures/prod_shape.sql can live in the repo.

Requires a running Postgres URL via DATABASE_URL or --url.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ORG = UUID("3c8a1e90-7b2f-4d11-9c4a-0f6b2a8d1e55")


def build(url: str, out: Path) -> None:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    from app import models  # noqa: F401
    from app.core.security import hash_password
    from app.db.base import Base, utcnow
    from app.models.client import Client
    from app.models.employee import Employee
    from app.models.invoice import Invoice
    from app.models.organization import Organization
    from app.models.project import Project, ProjectMember
    from app.models.task import Task
    from app.models.user import User
    from scripts.scrub_dump import scrub

    engine = create_engine(url)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        org = Organization(id=ORG, name="Studio Sunny", slug="studio-sunny")
        db.add(org)
        founder = User(
            id=uuid4(),
            email="founder@example.invalid",
            hashed_password=hash_password("ScrubbedPass1!"),
            first_name="Founder",
            last_name="Person",
            display_name="Founder Person",
            role_key="founder",
            org_id=ORG,
            is_active=True,
        )
        pm = User(
            id=uuid4(),
            email="pm@example.invalid",
            hashed_password=hash_password("ScrubbedPass1!"),
            first_name="Project",
            last_name="Manager",
            display_name="Project Manager",
            role_key="project_manager",
            org_id=ORG,
            is_active=True,
        )
        dev = User(
            id=uuid4(),
            email="dev@example.invalid",
            hashed_password=hash_password("ScrubbedPass1!"),
            first_name="Dev",
            last_name="Eloper",
            display_name="Dev Eloper",
            role_key="designer",
            org_id=ORG,
            is_active=True,
        )
        db.add_all([founder, pm, dev])
        db.flush()
        for u, title, sal in (
            (founder, "Founder", Decimal("100000")),
            (pm, "PM", Decimal("80000")),
            (dev, "Designer", Decimal("70000")),
        ):
            db.add(
                Employee(
                    user_id=u.id,
                    job_title=title,
                    employment_type="full_time",
                    salary=sal,
                    salary_currency="INR",
                    org_id=ORG,
                )
            )
        client = Client(
            id=uuid4(),
            business_name="Acme Widgets Pvt Ltd",
            slug="acme-widgets",
            email="billing@acme.example.invalid",
            phone="+91 90000 11111",
            status="active",
            org_id=ORG,
        )
        db.add(client)
        db.flush()
        project = Project(
            id=uuid4(),
            name="Acme Rebuild",
            slug="acme-rebuild",
            client_id=client.id,
            project_manager_id=pm.id,
            project_type="Website",
            status="in_progress",
            health="healthy",
            priority="high",
            progress=40,
            org_id=ORG,
        )
        db.add(project)
        db.flush()
        db.add(ProjectMember(project_id=project.id, user_id=pm.id, role_on_project="project_manager", org_id=ORG))
        db.add(ProjectMember(project_id=project.id, user_id=dev.id, role_on_project="contributor", org_id=ORG))
        for i in range(5):
            db.add(
                Task(
                    title=f"Delivery task {i}",
                    project_id=project.id,
                    assignee_id=dev.id,
                    created_by_id=pm.id,
                    status="todo" if i % 2 == 0 else "in_progress",
                    priority="medium",
                    org_id=ORG,
                )
            )
        db.add(
            Invoice(
                number="INV-2026-0001",
                client_id=client.id,
                project_id=project.id,
                amount=Decimal("250000.00"),
                tax=Decimal("0"),
                discount=Decimal("0"),
                currency="INR",
                due_date=date.today() + timedelta(days=30),
                issued_date=date.today(),
                status="sent",
                org_id=ORG,
            )
        )
        db.commit()

    # Dump as SQL INSERT-friendly pg_dump if available; else emit INSERT via SQLAlchemy
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        dump = subprocess.check_output(
            [
                "pg_dump",
                "--no-owner",
                "--no-privileges",
                "--inserts",
                url.replace("postgresql+psycopg://", "postgresql://"),
            ],
            text=True,
            stderr=subprocess.STDOUT,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        # Fallback: schema via metadata DDL + COPY-ish inserts as INSERTs
        from sqlalchemy.schema import CreateTable

        parts = ["BEGIN;", "SET client_encoding = 'UTF8';"]
        with engine.connect() as conn:
            for table in Base.metadata.sorted_tables:
                parts.append(str(CreateTable(table).compile(dialect=engine.dialect)) + ";")
            for table in Base.metadata.sorted_tables:
                rows = conn.execute(text(f"SELECT * FROM {table.name}")).mappings().all()
                if not rows:
                    continue
                cols = list(rows[0].keys())
                col_list = ", ".join(cols)
                for row in rows:
                    vals = []
                    for c in cols:
                        v = row[c]
                        if v is None:
                            vals.append("NULL")
                        elif isinstance(v, (int, float, Decimal)):
                            vals.append(str(v))
                        elif isinstance(v, bool):
                            vals.append("TRUE" if v else "FALSE")
                        else:
                            s = str(v).replace("'", "''")
                            vals.append(f"'{s}'")
                    parts.append(f"INSERT INTO {table.name} ({col_list}) VALUES ({', '.join(vals)});")
        parts.append("COMMIT;")
        dump = "\n".join(parts)

    scrubbed = scrub(dump)
    # Ensure alembic_version is absent so upgrade-over-data must run migrations
    scrubbed = "\n".join(line for line in scrubbed.splitlines() if "alembic_version" not in line.lower())
    out.write_text(scrubbed, encoding="utf-8")
    print(f"Wrote {out} ({out.stat().st_size} bytes)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="postgresql+psycopg://sunny:sunny_hq_dev@localhost:5432/studio_sunny_hq_shape")
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=ROOT / "tests" / "fixtures" / "prod_shape.sql",
    )
    args = ap.parse_args()
    build(args.url, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
