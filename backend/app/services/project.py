from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.task import Task


def recompute_project_progress(db: Session, project_id: UUID) -> Project | None:
    project = db.get(Project, project_id)
    if not project:
        return None

    total = db.scalar(
        select(func.count()).select_from(Task).where(
            Task.project_id == project_id,
            Task.deleted_at.is_(None),
            Task.parent_id.is_(None),
        )
    ) or 0
    done = db.scalar(
        select(func.count()).select_from(Task).where(
            Task.project_id == project_id,
            Task.deleted_at.is_(None),
            Task.parent_id.is_(None),
            Task.status == "completed",
        )
    ) or 0

    project.progress = int(round((done / total) * 100)) if total else 0
    db.add(project)
    return project


def slugify(value: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "item"
