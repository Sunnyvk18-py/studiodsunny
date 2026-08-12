from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.authz import is_founder, is_founder_or_pm, project_member_ids
from app.core.deps import CurrentUser, DbDep
from app.core.pagination import LimitQuery, apply_created_before_cursor, clamp_limit
from app.models.activity import Activity
from app.models.user import User
from app.schemas.common import UserBrief
from app.schemas.misc import ActivityOut

router = APIRouter()


@router.get("", response_model=list[ActivityOut])
def list_activity(
    db: DbDep,
    user: CurrentUser,
    project_id: UUID | None = None,
    limit: int = LimitQuery(40),
    before: datetime | None = Query(None, description="Cursor: created_at strictly before"),
):
    limit = clamp_limit(limit)
    member_projects = project_member_ids(db, user.id)
    stmt = select(Activity)
    if project_id:
        stmt = stmt.where(Activity.project_id == project_id)
    if not (is_founder(user) or is_founder_or_pm(user)):
        personal = (Activity.actor_id == user.id) & (Activity.project_id.is_(None))
        if member_projects:
            stmt = stmt.where((Activity.project_id.in_(member_projects)) | personal)
        else:
            stmt = stmt.where(personal)
    stmt = apply_created_before_cursor(stmt, Activity, before).limit(limit)
    rows = list(db.scalars(stmt).all())

    actor_ids = [a.actor_id for a in rows if a.actor_id]
    actors = {u.id: u for u in db.scalars(select(User).where(User.id.in_(actor_ids))).all()} if actor_ids else {}
    out = []
    for a in rows:
        actor = actors.get(a.actor_id) if a.actor_id else None
        out.append(
            ActivityOut(
                id=a.id,
                actor_id=a.actor_id,
                verb=a.verb,
                entity_type=a.entity_type,
                entity_id=a.entity_id,
                project_id=a.project_id,
                client_id=a.client_id,
                summary=a.summary,
                meta=a.meta or {},
                created_at=a.created_at,
                actor=UserBrief.model_validate(actor) if actor else None,
            )
        )
    return out
