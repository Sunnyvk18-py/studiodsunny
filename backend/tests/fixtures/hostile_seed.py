"""Hostile but valid seed data for render / timing stress tests."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.core.tenant import STUDIO_SUNNY_ORG_ID
from app.db.base import utcnow
from app.models.chat import ChatChannel, ChatChannelMember, ChatMessage
from app.models.client import Client
from app.models.employee import Employee
from app.models.file_asset import FileAsset
from app.models.invoice import Invoice
from app.models.project import Project, ProjectMember
from app.models.task import Task
from app.models.user import User

HOSTILE_STRINGS = [
    "👨‍👩‍👧",  # ZWJ family emoji
    "مرحبا بالعالم",  # Arabic RTL
    "שלום עולם",  # Hebrew RTL
    "N" * 400,  # long name
    "<script>alert(1)</script>",
    "'; DROP TABLE users;--",
    "=cmd|'/C calc'!A0",  # Excel formula injection
    "null\x00byte",
    "lone-surrogate-\ufffd",  # stand-in for lone surrogate (U+FFFD)
]


def load_hostile_seed(db: Session) -> dict:
    """Populate deliberately difficult rows. Returns ids for assertions."""
    org = STUDIO_SUNNY_ORG_ID
    pw = hash_password("HostileSeed2026!")

    founder = db.scalar(select(User).where(User.email == "sunny@studiosunny.com"))
    if not founder:
        founder = User(
            email="sunny@studiosunny.com",
            hashed_password=pw,
            first_name="Sunny",
            last_name="Founder",
            display_name="Sunny",
            role_key="founder",
            org_id=org,
            is_active=True,
        )
        db.add(founder)
        db.flush()

    # Soft-deleted user still referenced by a live task
    deleted_user = User(
        email=f"deleted-{uuid4().hex[:8]}@hostile.invalid",
        hashed_password=pw,
        first_name=HOSTILE_STRINGS[0],
        last_name=HOSTILE_STRINGS[1],
        display_name=HOSTILE_STRINGS[4],
        role_key="developer",
        org_id=org,
        is_active=False,
        deleted_at=utcnow(),
    )
    db.add(deleted_user)
    db.flush()

    # Manager who will be soft-deleted
    manager_user = User(
        email=f"mgr-{uuid4().hex[:8]}@hostile.invalid",
        hashed_password=pw,
        first_name="Mgr",
        last_name=HOSTILE_STRINGS[2],
        display_name=HOSTILE_STRINGS[5],
        role_key="project_manager",
        org_id=org,
        is_active=True,
    )
    db.add(manager_user)
    db.flush()
    manager_emp = Employee(
        user_id=manager_user.id,
        job_title=HOSTILE_STRINGS[3][:160],
        employment_type="full_time",
        salary=Decimal("0"),
        org_id=org,
    )
    db.add(manager_emp)
    db.flush()

    orphan_user = User(
        email=f"orphan-{uuid4().hex[:8]}@hostile.invalid",
        hashed_password=pw,
        first_name="Orphan",
        last_name="NoAssign",
        display_name="Orphan",
        role_key="designer",
        org_id=org,
        is_active=True,
    )
    db.add(orphan_user)
    db.flush()
    orphan_emp = Employee(
        user_id=orphan_user.id,
        job_title="Unassigned",
        employment_type="full_time",
        manager_id=manager_emp.id,
        salary=Decimal("-1.00"),
        salary_currency="JPY",
        org_id=org,
    )
    db.add(orphan_emp)
    # Soft-delete manager after FK is set
    manager_user.deleted_at = utcnow()
    manager_user.is_active = False
    db.add(manager_user)

    empty_client = Client(
        business_name=HOSTILE_STRINGS[6],
        slug=f"hostile-empty-{uuid4().hex[:6]}",
        email="hostile@example.invalid",
        status="active",
        org_id=org,
    )
    rich_client = Client(
        business_name=HOSTILE_STRINGS[3][:200],
        slug=f"hostile-rich-{uuid4().hex[:6]}",
        primary_contact_name=HOSTILE_STRINGS[0],
        notes=HOSTILE_STRINGS[7],
        status="active",
        org_id=org,
    )
    db.add_all([empty_client, rich_client])
    db.flush()

    empty_project = Project(
        name="Hostile Empty Project",
        slug=f"hostile-empty-p-{uuid4().hex[:6]}",
        client_id=rich_client.id,
        project_manager_id=founder.id,
        project_type="Website",
        status="planning",
        health="healthy",
        org_id=org,
    )
    huge_project = Project(
        name="Hostile 5k Tasks",
        slug=f"hostile-5k-{uuid4().hex[:6]}",
        client_id=rich_client.id,
        project_manager_id=founder.id,
        project_type="Website",
        status="in_progress",
        health="healthy",
        description=HOSTILE_STRINGS[1],
        org_id=org,
    )
    archived_project = Project(
        name="Hostile Archived",
        slug=f"hostile-arch-{uuid4().hex[:6]}",
        client_id=rich_client.id,
        project_manager_id=founder.id,
        project_type="App",
        status="completed",
        health="healthy",
        deleted_at=utcnow(),
        org_id=org,
    )
    db.add_all([empty_project, huge_project, archived_project])
    db.flush()
    for p in (empty_project, huge_project):
        db.add(ProjectMember(project_id=p.id, user_id=founder.id, role_on_project="founder", org_id=org))

    # Task on archived project + task assigned to soft-deleted user
    db.add(
        Task(
            title=HOSTILE_STRINGS[5],
            project_id=archived_project.id,
            assignee_id=deleted_user.id,
            created_by_id=founder.id,
            status="todo",
            priority="urgent",
            org_id=org,
        )
    )

    # 5000 tasks (bulk)
    bulk = [
        Task(
            title=f"Hostile bulk {i} {HOSTILE_STRINGS[i % len(HOSTILE_STRINGS)][:40]}",
            project_id=huge_project.id,
            assignee_id=founder.id if i % 10 == 0 else None,
            created_by_id=founder.id,
            status="todo" if i % 3 else "completed",
            priority="low",
            org_id=org,
        )
        for i in range(5000)
    ]
    db.add_all(bulk)

    # Money edge cases
    for amount, currency, status in (
        (Decimal("0"), "INR", "draft"),
        (Decimal("-50.00"), "INR", "draft"),
        (Decimal("999999999.99"), "INR", "sent"),
        (Decimal("1000"), "JPY", "paid"),
    ):
        db.add(
            Invoice(
                number=f"HINV-{uuid4().hex[:8]}",
                client_id=rich_client.id,
                project_id=huge_project.id,
                amount=amount,
                tax=Decimal("0"),
                discount=Decimal("0"),
                currency=currency,
                status=status,
                org_id=org,
            )
        )

    # DST / leap / extreme TZ timestamps on users
    leap = datetime(2024, 2, 29, 12, 0, tzinfo=timezone.utc)
    dst = datetime(2026, 3, 8, 2, 30, tzinfo=timezone.utc)  # US spring-forward window
    founder.last_login_at = leap
    orphan_user.last_login_at = dst
    db.add(founder)
    db.add(orphan_user)
    # Encode extreme offsets in location field (no dedicated TZ column on user)
    orphan_emp.location = "UTC+14 / UTC-11"
    db.add(orphan_emp)

    # Files
    db.add(
        FileAsset(
            name="hostile.svg",
            original_name="hostile.svg",
            storage_key=f"hostile/{uuid4().hex}.svg",
            mime_type="image/svg+xml",
            size_bytes=128,
            uploaded_by_id=founder.id,
            org_id=org,
        )
    )
    db.add(
        FileAsset(
            name="../../etc/passwd",
            original_name="../../etc/passwd",
            storage_key=f"hostile/{uuid4().hex}.bin",
            mime_type="application/octet-stream",
            size_bytes=32,
            uploaded_by_id=founder.id,
            org_id=org,
        )
    )

    # Chat with 10k messages
    channel = ChatChannel(
        slug=f"hostile-{uuid4().hex[:6]}",
        name=HOSTILE_STRINGS[0],
        topic=HOSTILE_STRINGS[4],
        kind="channel",
        org_id=org,
    )
    db.add(channel)
    db.flush()
    db.add(ChatChannelMember(channel_id=channel.id, user_id=founder.id, org_id=org))
    msgs = [
        ChatMessage(
            channel_id=channel.id,
            author_id=founder.id,
            body=HOSTILE_STRINGS[i % len(HOSTILE_STRINGS)][:500],
            org_id=org,
            created_at=utcnow() - timedelta(seconds=i),
        )
        for i in range(10_000)
    ]
    db.add_all(msgs)
    db.commit()
    return {
        "huge_project_id": str(huge_project.id),
        "empty_project_id": str(empty_project.id),
        "channel_slug": channel.slug,
        "orphan_email": orphan_user.email,
    }
