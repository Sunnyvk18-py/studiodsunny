from datetime import date, timedelta

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import or_, select

from app.core.authz import is_founder, is_founder_or_pm, is_project_member, project_member_ids
from app.core.deps import CurrentUser, DbDep
from app.models.project import Project, ProjectMilestone
from app.models.task import Task

router = APIRouter()


class CalendarEvent(BaseModel):
    id: str
    title: str
    date: date
    kind: str  # task | milestone
    status: str | None = None
    project_id: str | None = None
    project_name: str | None = None
    href: str | None = None
    priority: str | None = None


@router.get("/events", response_model=list[CalendarEvent])
def list_events(
    db: DbDep,
    user: CurrentUser,
    start: date | None = None,
    end: date | None = None,
    mine: bool = Query(False),
):
    today = date.today()
    start = start or (today - timedelta(days=7))
    end = end or (today + timedelta(days=45))
    member_projects = project_member_ids(db, user.id)
    events: list[CalendarEvent] = []

    task_q = select(Task).where(
        Task.deleted_at.is_(None),
        Task.due_date.is_not(None),
        Task.due_date >= start,
        Task.due_date <= end,
    )
    if mine:
        task_q = task_q.where(
            or_(Task.assignee_id == user.id, Task.reviewer_id == user.id, Task.created_by_id == user.id)
        )
    tasks = db.scalars(task_q.order_by(Task.due_date.asc())).all()
    visible_tasks = []
    for t in tasks:
        if is_founder(user) or is_founder_or_pm(user):
            visible_tasks.append(t)
        elif t.assignee_id == user.id or t.reviewer_id == user.id or t.created_by_id == user.id:
            visible_tasks.append(t)
        elif t.project_id and t.project_id in member_projects:
            visible_tasks.append(t)

    project_ids = {t.project_id for t in visible_tasks if t.project_id}
    projects = (
        {p.id: p for p in db.scalars(select(Project).where(Project.id.in_(project_ids))).all()} if project_ids else {}
    )

    for t in visible_tasks:
        p = projects.get(t.project_id) if t.project_id else None
        href = "/desk" if t.assignee_id == user.id else f"/tasks?id={t.id}"
        events.append(
            CalendarEvent(
                id=f"task:{t.id}",
                title=t.title,
                date=t.due_date,
                kind="task",
                status=t.status,
                project_id=str(t.project_id) if t.project_id else None,
                project_name=p.name if p else None,
                href=href,
                priority=t.priority,
            )
        )

    ms_q = (
        select(ProjectMilestone, Project)
        .join(Project, Project.id == ProjectMilestone.project_id)
        .where(
            Project.deleted_at.is_(None),
            ProjectMilestone.due_date.is_not(None),
            ProjectMilestone.due_date >= start,
            ProjectMilestone.due_date <= end,
        )
        .order_by(ProjectMilestone.due_date.asc())
    )
    for ms, project in db.execute(ms_q).all():
        if not (is_founder(user) or is_founder_or_pm(user) or project.id in member_projects):
            continue
        events.append(
            CalendarEvent(
                id=f"milestone:{ms.id}",
                title=ms.title,
                date=ms.due_date,
                kind="milestone",
                status=ms.status,
                project_id=str(project.id),
                project_name=project.name,
                href=f"/projects/{project.id}",
            )
        )

    events.sort(key=lambda e: (e.date, e.kind, e.title))
    return events
