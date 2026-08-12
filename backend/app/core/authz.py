"""Authorization helpers aligned to PERMISSIONS.md (not ROLE_PERMISSIONS alone)."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import ProjectMember
from app.models.user import User

# Matrix roles (PERMISSIONS.md). Code keys:
PM_ROLES = frozenset({"project_manager"})
FOUNDER_ROLES = frozenset({"founder"})


def is_founder(user: User) -> bool:
    return user.role_key in FOUNDER_ROLES or bool(user.is_superadmin)


def is_pm(user: User) -> bool:
    return user.role_key in PM_ROLES


def is_founder_or_pm(user: User) -> bool:
    return is_founder(user) or is_pm(user)


def require_founder(user: User) -> None:
    if not is_founder(user):
        raise HTTPException(403, "Insufficient permissions")


def require_founder_or_pm(user: User) -> None:
    if not is_founder_or_pm(user):
        raise HTTPException(403, "Insufficient permissions")


def not_found(entity: str = "Resource") -> HTTPException:
    """Same message for missing and forbidden-by-membership (no enumeration oracle)."""
    return HTTPException(404, f"{entity} not found")


def project_member_ids(db: Session, user_id: UUID) -> set[UUID]:
    rows = db.scalars(select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)).all()
    return set(rows)


def is_project_member(db: Session, user: User, project_id: UUID | None) -> bool:
    """Strict membership (or PM of that project). Does not elevate founder/pm globally."""
    if project_id is None:
        return False
    from app.models.project import Project

    p = db.get(Project, project_id)
    if p and p.project_manager_id == user.id:
        return True
    return (
        db.scalar(
            select(ProjectMember.id).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user.id,
            )
        )
        is not None
    )


def can_see_project(db: Session, user: User, project_id: UUID | None) -> bool:
    if is_founder_or_pm(user):
        return True
    return is_project_member(db, user, project_id)


def require_project_member(db: Session, user: User, project_id: UUID | None, *, entity: str = "Resource") -> None:
    if not is_project_member(db, user, project_id):
        raise not_found(entity)
