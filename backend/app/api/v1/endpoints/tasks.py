from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.authz import is_founder, is_founder_or_pm, is_project_member, not_found
from app.core.pagination import LimitQuery, apply_created_before_cursor, clamp_limit
from app.core.deps import CurrentUser, DbDep
from app.core.permissions import Perm, role_has_permission
from app.core.tenant import tenant_id
from app.db.base import utcnow
from app.models.project import Project, ProjectMember
from app.models.task import Task, TaskComment
from app.models.user import User
from app.schemas.common import UserBrief
from app.schemas.task import TaskCommentCreate, TaskCommentOut, TaskCommentUpdate, TaskCreate, TaskOut, TaskUpdate
from app.services.activity import audit, log_activity, notify
from app.services.project import recompute_project_progress

router = APIRouter()


def _task_out(db, t: Task) -> TaskOut:
    project = db.get(Project, t.project_id) if t.project_id else None
    assignee = db.get(User, t.assignee_id) if t.assignee_id else None
    reviewer = db.get(User, t.reviewer_id) if t.reviewer_id else None
    data = TaskOut.model_validate(t)
    data.project_name = project.name if project else None
    data.assignee_name = assignee.display_name if assignee else None
    data.reviewer_name = reviewer.display_name if reviewer else None
    data.archived = t.deleted_at is not None
    return data


def _can_see_task(db, user: User, t: Task) -> bool:
    if is_founder(user) or is_founder_or_pm(user):
        return True
    if t.assignee_id == user.id or t.reviewer_id == user.id or t.created_by_id == user.id:
        return True
    if t.project_id:
        return is_project_member(db, user, t.project_id)
    return False


def _can_patch_task(db, user: User, t: Task) -> bool:
    if is_founder(user) or is_founder_or_pm(user):
        return True
    return t.assignee_id == user.id


@router.get("", response_model=list[TaskOut])
def list_tasks(
    db: DbDep,
    user: CurrentUser,
    project_id: UUID | None = None,
    assignee_id: UUID | None = None,
    status_filter: str | None = Query(None, alias="status"),
    mine: bool = False,
    archived: bool = False,
    limit: int = LimitQuery(50),
    before: datetime | None = Query(
        None,
        description="Cursor: return tasks with created_at strictly before this timestamp",
    ),
):
    """Cursor-paginated task list. Hard server cap = HARD_MAX (not offset pages)."""
    limit = clamp_limit(limit)
    stmt = select(Task)
    if archived:
        stmt = stmt.where(Task.deleted_at.is_not(None))
    else:
        stmt = stmt.where(Task.deleted_at.is_(None))
    if project_id:
        stmt = stmt.where(Task.project_id == project_id)
    if assignee_id:
        stmt = stmt.where(Task.assignee_id == assignee_id)
    if mine:
        stmt = stmt.where(Task.assignee_id == user.id)
    if status_filter:
        stmt = stmt.where(Task.status == status_filter)
    if not (is_founder(user) or is_founder_or_pm(user)):
        # Membership / assignment scoped in SQL so the hard cap is real.
        member_ids = select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
        stmt = stmt.where(
            (Task.assignee_id == user.id)
            | (Task.reviewer_id == user.id)
            | (Task.created_by_id == user.id)
            | (Task.project_id.in_(member_ids))
        )
    stmt = apply_created_before_cursor(stmt, Task, before).limit(limit)
    tasks = list(db.scalars(stmt).all())
    return [_task_out(db, t) for t in tasks]


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: UUID, db: DbDep, user: CurrentUser):
    t = db.get(Task, task_id)
    if not t or not _can_see_task(db, user, t):
        raise not_found("Task")
    return _task_out(db, t)


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: DbDep, user: CurrentUser):
    if not role_has_permission(user.role_key, Perm.TASKS_WRITE):
        raise HTTPException(403, "Cannot create tasks")
    if not payload.project_id or not is_project_member(db, user, payload.project_id):
        # Right role but not a member of target project
        raise HTTPException(403, "Not a member of the target project")
    t = Task(**payload.model_dump(), created_by_id=user.id, org_id=tenant_id(user))
    if t.status == "in_progress" and not t.started_at:
        t.started_at = utcnow()
    db.add(t)
    db.flush()
    project = db.get(Project, t.project_id) if t.project_id else None
    log_activity(
        db,
        actor=user,
        verb="created",
        entity_type="task",
        entity_id=t.id,
        project_id=t.project_id,
        client_id=project.client_id if project else None,
        summary=f"{user.display_name} created task “{t.title}”",
    )
    if t.assignee_id and t.assignee_id != user.id:
        notify(
            db,
            user_id=t.assignee_id,
            type="task_assigned",
            title="New task assigned",
            body=f"{t.title}" + (f" · {project.name}" if project else ""),
            entity_type="task",
            entity_id=t.id,
            href=f"/tasks?id={t.id}",
            priority="high" if t.priority in ("high", "urgent") else "normal",
        )
    if t.project_id:
        recompute_project_progress(db, t.project_id)
    audit(db, user=user, action="task.create", entity_type="task", entity_id=t.id)
    db.commit()
    db.refresh(t)
    return _task_out(db, t)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: UUID, payload: TaskUpdate, db: DbDep, user: CurrentUser):
    t = db.get(Task, task_id)
    if not t or t.deleted_at or not _can_patch_task(db, user, t):
        raise not_found("Task")

    old_status = t.status
    old_assignee = t.assignee_id
    data = payload.model_dump(exclude_unset=True)

    if "status" in data:
        new_status = data["status"]
        if new_status == "in_progress" and not t.started_at:
            t.started_at = utcnow()
        if new_status == "completed":
            t.completed_at = utcnow()
        elif old_status == "completed" and new_status != "completed":
            t.completed_at = None

    for k, v in data.items():
        setattr(t, k, v)
    db.add(t)

    project = db.get(Project, t.project_id) if t.project_id else None
    if "status" in data and data["status"] != old_status:
        log_activity(
            db,
            actor=user,
            verb="status_changed",
            entity_type="task",
            entity_id=t.id,
            project_id=t.project_id,
            client_id=project.client_id if project else None,
            summary=f"{user.display_name} marked “{t.title}” as {data['status'].replace('_', ' ')}",
        )
        watchers = {t.created_by_id, t.assignee_id, t.reviewer_id, project.project_manager_id if project else None}
        for uid in watchers:
            if uid and uid != user.id:
                notify(
                    db,
                    user_id=uid,
                    type="task_updated",
                    title="Task updated",
                    body=f"{t.title} is now {data['status'].replace('_', ' ')}",
                    entity_type="task",
                    entity_id=t.id,
                    href="/desk",
                )
    if "assignee_id" in data and data["assignee_id"] and data["assignee_id"] != old_assignee:
        notify(
            db,
            user_id=data["assignee_id"],
            type="task_assigned",
            title="Task assigned to you",
            body=t.title,
            entity_type="task",
            entity_id=t.id,
            href="/desk",
        )

    if t.project_id:
        recompute_project_progress(db, t.project_id)
    audit(
        db,
        user=user,
        action="task.update",
        entity_type="task",
        entity_id=t.id,
        meta={"status": t.status} if "status" in data else {},
    )
    db.commit()
    db.refresh(t)
    return _task_out(db, t)


@router.post("/{task_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
def archive_task(task_id: UUID, db: DbDep, user: CurrentUser):
    t = db.get(Task, task_id)
    if not t or t.deleted_at or not _can_patch_task(db, user, t):
        raise not_found("Task")
    t.deleted_at = utcnow()
    db.add(t)
    if t.project_id:
        recompute_project_progress(db, t.project_id)
    audit(db, user=user, action="task.archive", entity_type="task", entity_id=t.id)
    db.commit()
    return None


@router.get("/{task_id}/comments", response_model=list[TaskCommentOut])
def list_comments(task_id: UUID, db: DbDep, user: CurrentUser):
    t = db.get(Task, task_id)
    if not t or not _can_see_task(db, user, t):
        raise not_found("Task")
    comments = db.scalars(
        select(TaskComment).where(TaskComment.task_id == t.id).order_by(TaskComment.created_at.asc())
    ).all()
    out = []
    for c in comments:
        author = db.get(User, c.author_id)
        item = TaskCommentOut.model_validate(c)
        item.author = UserBrief.model_validate(author) if author else None
        out.append(item)
    return out


@router.post("/{task_id}/comments", response_model=TaskCommentOut, status_code=201)
def add_comment(task_id: UUID, payload: TaskCommentCreate, db: DbDep, user: CurrentUser):
    t = db.get(Task, task_id)
    if not t or not _can_see_task(db, user, t):
        raise not_found("Task")
    c = TaskComment(task_id=t.id, author_id=user.id, body=payload.body, org_id=tenant_id(user))
    db.add(c)
    log_activity(
        db,
        actor=user,
        verb="commented",
        entity_type="task",
        entity_id=t.id,
        project_id=t.project_id,
        summary=f"{user.display_name} commented on “{t.title}”",
    )
    db.commit()
    db.refresh(c)
    out = TaskCommentOut.model_validate(c)
    out.author = UserBrief.model_validate(user)
    return out


@router.patch("/{task_id}/comments/{comment_id}", response_model=TaskCommentOut)
def update_comment(task_id: UUID, comment_id: UUID, payload: TaskCommentUpdate, db: DbDep, user: CurrentUser):
    t = db.get(Task, task_id)
    if not t or t.deleted_at or not _can_see_task(db, user, t):
        raise not_found("Task")
    c = db.get(TaskComment, comment_id)
    if not c or c.task_id != t.id:
        raise not_found("Comment")
    if not is_founder(user) and c.author_id != user.id:
        raise not_found("Comment")
    c.body = payload.body
    db.add(c)
    audit(db, user=user, action="task.comment_update", entity_type="task_comment", entity_id=c.id)
    db.commit()
    db.refresh(c)
    out = TaskCommentOut.model_validate(c)
    author = db.get(User, c.author_id)
    out.author = UserBrief.model_validate(author) if author else None
    return out


@router.delete("/{task_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(task_id: UUID, comment_id: UUID, db: DbDep, user: CurrentUser):
    t = db.get(Task, task_id)
    if not t or t.deleted_at or not _can_see_task(db, user, t):
        raise not_found("Task")
    c = db.get(TaskComment, comment_id)
    if not c or c.task_id != t.id:
        raise not_found("Comment")
    if not is_founder(user) and c.author_id != user.id:
        raise not_found("Comment")
    db.delete(c)
    audit(db, user=user, action="task.comment_delete", entity_type="task_comment", entity_id=comment_id)
    db.commit()
    return None
