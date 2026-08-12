from datetime import date, timedelta

from fastapi import APIRouter
from sqlalchemy import select

from app.core.deps import CurrentUser, DbDep
from app.models.activity import Activity
from app.models.notification import Notification
from app.models.project import Project, ProjectMember
from app.models.task import Task
from app.models.user import User
from app.schemas.common import UserBrief
from app.schemas.misc import ActivityOut, DeskOut, NotificationOut
from app.schemas.project import ProjectOut
from app.schemas.task import TaskOut

router = APIRouter()


def _task_out(db, t: Task) -> TaskOut:
    project = db.get(Project, t.project_id) if t.project_id else None
    assignee = db.get(User, t.assignee_id) if t.assignee_id else None
    reviewer = db.get(User, t.reviewer_id) if t.reviewer_id else None
    data = TaskOut.model_validate(t)
    data.project_name = project.name if project else None
    data.assignee_name = assignee.display_name if assignee else None
    data.reviewer_name = reviewer.display_name if reviewer else None
    return data


@router.get("", response_model=DeskOut)
def my_desk(db: DbDep, user: CurrentUser):
    today = date.today()
    mine = select(Task).where(
        Task.assignee_id == user.id,
        Task.deleted_at.is_(None),
    )

    open_mine = db.scalars(
        mine.where(Task.status.notin_(["completed"])).order_by(Task.due_date.asc())
    ).all()

    focus = [_task_out(db, t) for t in open_mine[:3]]
    due_today = [_task_out(db, t) for t in open_mine if t.due_date == today]
    upcoming = [
        _task_out(db, t)
        for t in open_mine
        if t.due_date and today < t.due_date <= today + timedelta(days=7)
    ]
    blocked = [_task_out(db, t) for t in open_mine if t.status == "blocked"]

    member_project_ids = db.scalars(
        select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
    ).all()
    projects = []
    can_see_all = user.role_key in ("founder", "operations_manager")
    if can_see_all or member_project_ids:
        q = select(Project).where(Project.deleted_at.is_(None))
        if not can_see_all:
            q = q.where(Project.id.in_(member_project_ids))
        for p in db.scalars(q.order_by(Project.updated_at.desc()).limit(8)).all():
            client = p.client
            projects.append(
                ProjectOut.model_validate(p).model_copy(
                    update={"client_name": client.business_name if client else None}
                )
            )

    notes = db.scalars(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(8)
    ).all()

    activities = db.scalars(select(Activity).order_by(Activity.created_at.desc()).limit(8)).all()
    actor_ids = [a.actor_id for a in activities if a.actor_id]
    actors = {u.id: u for u in db.scalars(select(User).where(User.id.in_(actor_ids))).all()} if actor_ids else {}
    activity_out = []
    for a in activities:
        actor = actors.get(a.actor_id) if a.actor_id else None
        activity_out.append(
            ActivityOut(
                **{k: getattr(a, k) for k in [
                    "id", "actor_id", "verb", "entity_type", "entity_id",
                    "project_id", "client_id", "summary", "created_at",
                ]},
                meta=a.meta or {},
                actor=UserBrief.model_validate(actor) if actor else None,
            )
        )

    return DeskOut(
        focus=[f.model_dump() for f in focus],
        due_today=[t.model_dump() for t in due_today],
        upcoming=[t.model_dump() for t in upcoming],
        blocked=[t.model_dump() for t in blocked],
        projects=[p.model_dump() for p in projects],
        notifications=[NotificationOut.model_validate(n) for n in notes],
        activity=activity_out,
    )
