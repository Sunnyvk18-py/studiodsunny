from fastapi import APIRouter
from sqlalchemy import func, select

from app.core.authz import is_founder, is_founder_or_pm, is_project_member, project_member_ids
from app.core.deps import CurrentUser, DbDep
from app.models.client import Client
from app.models.lead import Lead
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.schemas.misc import SearchHit, SearchOut

router = APIRouter()


@router.get("", response_model=SearchOut)
def search(db: DbDep, user: CurrentUser, q: str = ""):
    term = (q or "").strip()
    if len(term) < 1:
        return SearchOut(results=[])
    like = f"%{term.lower()}%"
    results: list[SearchHit] = []
    member_ids = project_member_ids(db, user.id)

    projects = db.scalars(
        select(Project).where(Project.deleted_at.is_(None), func.lower(Project.name).like(like)).limit(8)
    ).all()
    for p in projects:
        if is_founder(user) or is_founder_or_pm(user) or p.id in member_ids or p.project_manager_id == user.id:
            results.append(
                SearchHit(type="project", id=p.id, title=p.name, subtitle=p.project_type, href=f"/projects/{p.id}")
            )

    # Clients & leads: founder/pm only (PERMISSIONS.md)
    if is_founder_or_pm(user):
        clients = db.scalars(
            select(Client)
            .where(Client.deleted_at.is_(None), func.lower(Client.business_name).like(like))
            .limit(6)
        ).all()
        for c in clients:
            results.append(
                SearchHit(type="client", id=c.id, title=c.business_name, subtitle=c.industry, href=f"/clients/{c.id}")
            )
        leads = db.scalars(
            select(Lead).where(Lead.deleted_at.is_(None), func.lower(Lead.business_name).like(like)).limit(5)
        ).all()
        for lead in leads:
            results.append(
                SearchHit(
                    type="lead",
                    id=lead.id,
                    title=lead.business_name,
                    subtitle=lead.stage.replace("_", " "),
                    href="/leads",
                )
            )

    employees = db.scalars(
        select(User).where(User.deleted_at.is_(None), func.lower(User.display_name).like(like)).limit(6)
    ).all()
    for u in employees:
        results.append(
            SearchHit(
                type="employee",
                id=u.id,
                title=u.display_name,
                subtitle=u.role_key.replace("_", " "),
                href="/team",
            )
        )

    tasks = db.scalars(select(Task).where(Task.deleted_at.is_(None), func.lower(Task.title).like(like)).limit(8)).all()
    for t in tasks:
        if t.assignee_id == user.id or is_founder(user) or is_founder_or_pm(user) or (
            t.project_id and is_project_member(db, user, t.project_id)
        ):
            results.append(
                SearchHit(type="task", id=t.id, title=t.title, subtitle=t.status.replace("_", " "), href="/desk")
            )

    return SearchOut(results=results[:20])
