from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.core.deps import CurrentUser, DbDep
from app.db.base import utcnow
from app.models.notification import Notification
from app.schemas.misc import NotificationOut

router = APIRouter()


@router.get("", response_model=list[NotificationOut])
def list_notifications(db: DbDep, user: CurrentUser, unread_only: bool = False):
    stmt = (
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(80)
    )
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    return [NotificationOut.model_validate(n) for n in db.scalars(stmt).all()]


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: UUID, db: DbDep, user: CurrentUser):
    n = db.get(Notification, notification_id)
    if not n or n.user_id != user.id:
        raise HTTPException(404, "Notification not found")
    n.read_at = utcnow()
    db.add(n)
    db.commit()
    db.refresh(n)
    return NotificationOut.model_validate(n)


@router.post("/read-all")
def mark_all_read(db: DbDep, user: CurrentUser):
    notes = db.scalars(
        select(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None))
    ).all()
    now = utcnow()
    for n in notes:
        n.read_at = now
        db.add(n)
    db.commit()
    return {"message": f"Marked {len(notes)} as read"}
