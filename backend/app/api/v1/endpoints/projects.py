from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.authz import is_founder, is_founder_or_pm, is_pm, not_found, require_founder_or_pm
from app.core.deps import CurrentUser, DbDep
from app.core.tenant import tenant_id
from app.models.client import Client
from app.models.project import Project, ProjectMember, ProjectMilestone
from app.models.task import Task
from app.models.user import User
from app.schemas.common import UserBrief
from app.schemas.project import (
    MilestoneCreate,
    MilestoneOut,
    ProjectCreate,
    ProjectDetail,
    ProjectMemberOut,
    ProjectOut,
    ProjectUpdate,
)
from app.services.activity import audit, log_activity, notify
from app.services.project import recompute_project_progress
from app.utils import unique_slug

router = APIRouter()


def _can_see_project(db, user: User, project: Project) -> bool:
    from app.core.authz import can_see_project

    return can_see_project(db, user, project.id)


def _hydrate_list(db, p: Project) -> ProjectOut:
    client = db.get(Client, p.client_id)
    manager = db.get(User, p.project_manager_id) if p.project_manager_id else None
    team_count = db.scalar(
        select(func.count()).select_from(ProjectMember).where(ProjectMember.project_id == p.id)
    ) or 0
    open_tasks = db.scalar(
        select(func.count()).select_from(Task).where(
            Task.project_id == p.id, Task.deleted_at.is_(None), Task.status.notin_(["completed"])
        )
    ) or 0
    blocked = db.scalar(
        select(func.count()).select_from(Task).where(
            Task.project_id == p.id, Task.deleted_at.is_(None), Task.status == "blocked"
        )
    ) or 0
    out = ProjectOut.model_validate(p)
    out.client_name = client.business_name if client else None
    out.manager_name = manager.display_name if manager else None
    out.team_count = team_count
    out.open_tasks = open_tasks
    out.blocked_tasks = blocked
    return out


@router.get("", response_model=list[ProjectOut])
def list_projects(
    db: DbDep,
    user: CurrentUser,
    q: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    health: str | None = None,
    client_id: UUID | None = None,
):
    stmt = select(Project).where(Project.deleted_at.is_(None)).order_by(Project.updated_at.desc())
    if q:
        stmt = stmt.where(func.lower(Project.name).like(f"%{q.lower()}%"))
    if status_filter:
        stmt = stmt.where(Project.status == status_filter)
    if health:
        stmt = stmt.where(Project.health == health)
    if client_id:
        stmt = stmt.where(Project.client_id == client_id)

    projects = db.scalars(stmt).all()
    visible = [p for p in projects if _can_see_project(db, user, p)]
    return [_hydrate_list(db, p) for p in visible]


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: UUID, db: DbDep, user: CurrentUser):
    p = db.scalar(
        select(Project)
        .options(selectinload(Project.members), selectinload(Project.milestones))
        .where(Project.id == project_id)
    )
    if not p or p.deleted_at or not _can_see_project(db, user, p):
        raise not_found("Project")

    base = _hydrate_list(db, p)
    members = []
    for m in p.members:
        u = db.get(User, m.user_id)
        members.append(
            ProjectMemberOut(
                id=m.id,
                user_id=m.user_id,
                role_on_project=m.role_on_project,
                user=UserBrief.model_validate(u) if u else None,
            )
        )
    milestones = [MilestoneOut.model_validate(ms) for ms in sorted(p.milestones, key=lambda x: x.sort_order)]
    return ProjectDetail(**base.model_dump(), members=members, milestones=milestones)


@router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: DbDep, user: CurrentUser):
    require_founder_or_pm(user)
    client = db.get(Client, payload.client_id)
    if not client or client.deleted_at:
        raise HTTPException(400, "Client not found")

    project = Project(
        name=payload.name,
        slug=unique_slug(db, Project, payload.name),
        client_id=payload.client_id,
        project_type=payload.project_type,
        description=payload.description,
        project_manager_id=payload.project_manager_id,
        start_date=payload.start_date,
        target_completion_date=payload.target_completion_date,
        budget=payload.budget,
        budget_currency=payload.budget_currency,
        priority=payload.priority,
        tech_stack=payload.tech_stack,
        repository_url=payload.repository_url,
        production_url=payload.production_url,
        staging_url=payload.staging_url,
        status="planning",
        health="healthy",
        org_id=tenant_id(user),
    )
    db.add(project)
    db.flush()

    member_ids = set(payload.member_ids)
    if payload.project_manager_id:
        member_ids.add(payload.project_manager_id)
    member_ids.add(user.id)

    for uid in member_ids:
        role = "project_manager" if uid == payload.project_manager_id else "contributor"
        db.add(ProjectMember(project_id=project.id, user_id=uid, role_on_project=role, org_id=tenant_id(user)))
        if uid != user.id:
            notify(
                db,
                user_id=uid,
                type="project_assigned",
                title="Added to project",
                body=f"You were added to {project.name}",
                entity_type="project",
                entity_id=project.id,
                href=f"/projects/{project.id}",
            )

    log_activity(
        db,
        actor=user,
        verb="created",
        entity_type="project",
        entity_id=project.id,
        project_id=project.id,
        client_id=project.client_id,
        summary=f"{user.display_name} created project {project.name}",
    )
    audit(db, user=user, action="project.create", entity_type="project", entity_id=project.id)
    db.commit()
    return get_project(project.id, db, user)


@router.patch("/{project_id}", response_model=ProjectDetail)
def update_project(project_id: UUID, payload: ProjectUpdate, db: DbDep, user: CurrentUser):
    if not is_founder_or_pm(user):
        raise not_found("Project")
    p = db.get(Project, project_id)
    if not p or p.deleted_at:
        raise not_found("Project")

    data = payload.model_dump(exclude_unset=True)
    member_ids = data.pop("member_ids", None)
    old_status = p.status
    for k, v in data.items():
        setattr(p, k, v)
    db.add(p)

    if member_ids is not None:
        existing = db.scalars(select(ProjectMember).where(ProjectMember.project_id == p.id)).all()
        existing_ids = {m.user_id for m in existing}
        wanted = set(member_ids)
        if p.project_manager_id:
            wanted.add(p.project_manager_id)
        for m in existing:
            if m.user_id not in wanted:
                db.delete(m)
        for uid in wanted - existing_ids:
            db.add(ProjectMember(project_id=p.id, user_id=uid, role_on_project="contributor", org_id=tenant_id(user)))
            notify(
                db,
                user_id=uid,
                type="project_assigned",
                title="Added to project",
                body=f"You were added to {p.name}",
                entity_type="project",
                entity_id=p.id,
                href=f"/projects/{p.id}",
            )

    if "status" in data and data["status"] != old_status:
        log_activity(
            db,
            actor=user,
            verb="status_changed",
            entity_type="project",
            entity_id=p.id,
            project_id=p.id,
            client_id=p.client_id,
            summary=f"{p.name} moved to {data['status'].replace('_', ' ')}",
        )
        members = db.scalars(select(ProjectMember).where(ProjectMember.project_id == p.id)).all()
        for m in members:
            if m.user_id != user.id:
                notify(
                    db,
                    user_id=m.user_id,
                    type="project_status",
                    title="Project status updated",
                    body=f"{p.name} is now {data['status'].replace('_', ' ')}",
                    entity_type="project",
                    entity_id=p.id,
                    href=f"/projects/{p.id}",
                )

    audit(db, user=user, action="project.update", entity_type="project", entity_id=p.id)
    db.commit()
    return get_project(project_id, db, user)


@router.post("/{project_id}/milestones", response_model=MilestoneOut, status_code=201)
def create_milestone(project_id: UUID, payload: MilestoneCreate, db: DbDep, user: CurrentUser):
    if not is_founder_or_pm(user):
        raise not_found("Project")
    p = db.get(Project, project_id)
    if not p or p.deleted_at:
        raise not_found("Project")
    ms = ProjectMilestone(project_id=p.id, org_id=tenant_id(user), **payload.model_dump())
    db.add(ms)
    log_activity(
        db,
        actor=user,
        verb="created",
        entity_type="milestone",
        entity_id=None,
        project_id=p.id,
        client_id=p.client_id,
        summary=f"{user.display_name} added milestone “{payload.title}” on {p.name}",
    )
    db.commit()
    db.refresh(ms)
    return MilestoneOut.model_validate(ms)


@router.post("/{project_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
def archive_project(project_id: UUID, db: DbDep, user: CurrentUser):
    from app.db.base import utcnow

    if not is_founder_or_pm(user):
        raise not_found("Project")
    p = db.get(Project, project_id)
    if not p or p.deleted_at:
        raise not_found("Project")
    p.deleted_at = utcnow()
    db.add(p)
    audit(db, user=user, action="project.archive", entity_type="project", entity_id=p.id)
    log_activity(
        db,
        actor=user,
        verb="archived",
        entity_type="project",
        entity_id=p.id,
        project_id=p.id,
        client_id=p.client_id,
        summary=f"{user.display_name} archived {p.name}",
    )
    db.commit()
    return None
