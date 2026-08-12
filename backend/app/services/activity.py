from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.tenant import STUDIO_SUNNY_ORG_ID, tenant_id
from app.models.activity import Activity
from app.models.notification import Notification
from app.models.user import User


def log_activity(
    db: Session,
    *,
    actor: User | None,
    verb: str,
    entity_type: str,
    summary: str,
    entity_id: UUID | None = None,
    project_id: UUID | None = None,
    client_id: UUID | None = None,
    meta: dict | None = None,
) -> Activity:
    activity = Activity(
        actor_id=actor.id if actor else None,
        org_id=tenant_id(actor) if actor else STUDIO_SUNNY_ORG_ID,
        verb=verb,
        entity_type=entity_type,
        entity_id=entity_id,
        project_id=project_id,
        client_id=client_id,
        summary=summary,
        meta=meta or {},
    )
    db.add(activity)
    db.flush()
    return activity


def notify(
    db: Session,
    *,
    user_id: UUID,
    type: str,
    title: str,
    body: str,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    href: str | None = None,
    priority: str = "normal",
    org_id: UUID | None = None,
) -> Notification:
    if org_id is None:
        recipient = db.get(User, user_id)
        org_id = tenant_id(recipient) if recipient else STUDIO_SUNNY_ORG_ID
    n = Notification(
        user_id=user_id,
        org_id=org_id,
        type=type,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
        href=href,
        priority=priority,
    )
    db.add(n)
    db.flush()
    return n


def audit(
    db: Session,
    *,
    user: User | None,
    action: str,
    entity_type: str,
    entity_id: UUID | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    request: Request | None = None,
    meta: dict | None = None,
) -> None:
    from app.models.audit import AuditLog

    if request is not None:
        ip = ip or (request.client.host if request.client else None)
        ua = request.headers.get("user-agent") or ""
        user_agent = user_agent or ua[:300]
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            org_id=tenant_id(user) if user else STUDIO_SUNNY_ORG_ID,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip,
            user_agent=user_agent,
            meta=meta or {},
        )
    )
