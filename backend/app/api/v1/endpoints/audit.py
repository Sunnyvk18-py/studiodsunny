from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import or_, select

from app.core.authz import require_founder
from app.core.deps import CurrentUser, DbDep
from app.core.pagination import LimitQuery, apply_created_before_cursor, clamp_limit
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.common import ORMModel

router = APIRouter()


class AuditOut(ORMModel):
    id: UUID
    user_id: UUID | None
    action: str
    entity_type: str
    entity_id: UUID | None
    ip_address: str | None
    user_agent: str | None = None
    meta: dict
    created_at: datetime
    user_name: str | None = None
    user_email: str | None = None


@router.get("", response_model=list[AuditOut])
def list_audit(
    db: DbDep,
    user: CurrentUser,
    limit: int = LimitQuery(50),
    before: datetime | None = Query(None, description="Cursor: created_at strictly before"),
    q: str | None = None,
    action: str | None = None,
    entity_type: str | None = None,
):
    require_founder(user)
    limit = clamp_limit(limit)
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action.ilike(f"%{action.strip()}%"))
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(AuditLog.action.ilike(like), AuditLog.entity_type.ilike(like)))
    stmt = apply_created_before_cursor(stmt, AuditLog, before).limit(limit)
    rows = list(db.scalars(stmt).all())
    user_ids = {r.user_id for r in rows if r.user_id}
    users = {
        u.id: u
        for u in (db.scalars(select(User).where(User.id.in_(user_ids))).all() if user_ids else [])
    }
    out: list[AuditOut] = []
    for row in rows:
        actor = users.get(row.user_id) if row.user_id else None
        item = AuditOut.model_validate(row)
        item.user_name = actor.display_name if actor else None
        item.user_email = actor.email if actor else None
        out.append(item)
    return out
