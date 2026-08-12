"""Arq worker — digests, standup nudges, and future embeddings."""

from __future__ import annotations

import logging
from datetime import date

from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings
from app.core.tenant import STUDIO_SUNNY_ORG_ID
from app.db.session import SessionLocal
from app.models.notification import Notification
from app.models.task import Task
from app.models.user import User
from sqlalchemy import func, select

logger = logging.getLogger("sunny.worker")


def _redis_settings() -> RedisSettings:
    # arq expects host/port; parse common redis URL forms
    url = settings.redis_url.replace("redis://", "")
    host_port, _, db = url.partition("/")
    host, _, port = host_port.partition(":")
    return RedisSettings(
        host=host or "localhost",
        port=int(port or 6379),
        database=int(db or 0),
    )


async def daily_digest(ctx) -> dict:
    """Notify each active user of open assigned tasks (in-app)."""
    db = SessionLocal()
    created = 0
    try:
        users = db.scalars(select(User).where(User.is_active.is_(True), User.deleted_at.is_(None))).all()
        today = date.today().isoformat()
        for user in users:
            open_count = db.scalar(
                select(func.count())
                .select_from(Task)
                .where(
                    Task.assignee_id == user.id,
                    Task.deleted_at.is_(None),
                    Task.status.notin_(("completed", "cancelled")),
                )
            ) or 0
            if open_count == 0:
                continue
            db.add(
                Notification(
                    user_id=user.id,
                    org_id=getattr(user, "org_id", None) or STUDIO_SUNNY_ORG_ID,
                    type="digest",
                    title="Daily desk digest",
                    body=f"You have {open_count} open task{'s' if open_count != 1 else ''} · {today}",
                    href="/desk",
                    priority="normal",
                )
            )
            created += 1
        db.commit()
        logger.info("daily_digest created=%s", created)
        return {"created": created}
    finally:
        db.close()


async def standup_reminder(ctx) -> dict:
    """Weekday standup nudge to founders/PMs."""
    db = SessionLocal()
    created = 0
    try:
        targets = db.scalars(
            select(User).where(
                User.is_active.is_(True),
                User.deleted_at.is_(None),
                User.role_key.in_(("founder", "operations_manager", "project_manager")),
            )
        ).all()
        for user in targets:
            db.add(
                Notification(
                    user_id=user.id,
                    org_id=getattr(user, "org_id", None) or STUDIO_SUNNY_ORG_ID,
                    type="standup",
                    title="Standup",
                    body="Post a short update in #general — blockers and ship plan.",
                    href="/messages",
                    priority="normal",
                )
            )
            created += 1
        db.commit()
        logger.info("standup_reminder created=%s", created)
        return {"created": created}
    finally:
        db.close()


async def enqueue_embedding_stub(ctx, doc_id: str) -> dict:
    """Placeholder for Phase 3 RAG embeddings."""
    logger.info("embedding stub for doc %s", doc_id)
    return {"doc_id": doc_id, "status": "queued_stub"}


async def on_startup(ctx):
    logger.info("Arq worker started")
    await heartbeat(ctx)


async def on_shutdown(ctx):
    logger.info("Arq worker stopped")


async def heartbeat(ctx) -> dict:
    """Keep Integrations page aware the worker is alive."""
    try:
        import redis as redis_lib
        from datetime import datetime, timezone

        r = redis_lib.from_url(settings.redis_url)
        stamp = datetime.now(timezone.utc).isoformat()
        r.set("hq:worker:heartbeat", stamp, ex=600)
        return {"ok": True, "at": stamp}
    except Exception as exc:
        logger.warning("heartbeat failed: %s", exc)
        return {"ok": False, "error": str(exc)}


class WorkerSettings:
    functions = [daily_digest, standup_reminder, enqueue_embedding_stub, heartbeat]
    cron_jobs = [
        cron(daily_digest, hour=9, minute=0),
        cron(standup_reminder, weekday={0, 1, 2, 3, 4}, hour=10, minute=0),
        cron(heartbeat, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
    ]
    redis_settings = _redis_settings()
    max_jobs = 10
    on_startup = on_startup
    on_shutdown = on_shutdown
