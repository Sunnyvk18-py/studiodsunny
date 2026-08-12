from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.authz import is_founder, is_founder_or_pm, not_found, require_founder, require_founder_or_pm
from app.core.deps import CurrentUser, DbDep
from app.core.permissions import Perm, ROLE_LABELS, role_has_permission
from app.core.security import hash_password
from app.models.department import Department
from app.models.employee import Employee
from app.models.project import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.schemas.employee import DepartmentOut, EmployeeCreate, EmployeeInvite, EmployeeOut, EmployeeUpdate
from app.services.activity import audit, log_activity
from app.models.auth_token import AuthToken
from app.core.config import settings
from app.core.tenant import tenant_id
from app.db.base import utcnow
from app.services.email import send_email
from app.utils import hash_token
from datetime import timedelta
import secrets

router = APIRouter()


def _utilization(db, user_id) -> tuple[int, int]:
    active_projects = db.scalar(
        select(func.count()).select_from(ProjectMember).where(ProjectMember.user_id == user_id)
    ) or 0
    open_tasks = db.scalar(
        select(func.count()).select_from(Task).where(
            Task.assignee_id == user_id,
            Task.deleted_at.is_(None),
            Task.status.notin_(["completed", "backlog"]),
        )
    ) or 0
    util = min(100, int((open_tasks / 6) * 100)) if open_tasks else (18 if active_projects else 8)
    return active_projects, util


def hydrate(db, emp: Employee, viewer: User) -> EmployeeOut:
    u = emp.user
    dept = emp.department
    active_projects, util = _utilization(db, u.id)
    show_comp = is_founder(viewer) or viewer.id == u.id
    return EmployeeOut(
        id=emp.id,
        user_id=u.id,
        display_name=u.display_name,
        email=u.email,
        first_name=u.first_name,
        last_name=u.last_name,
        avatar_url=u.avatar_url,
        role_key=u.role_key,
        job_title=emp.job_title,
        department_id=emp.department_id,
        department_name=dept.name if dept else None,
        manager_id=emp.manager_id,
        employment_type=emp.employment_type,
        location=emp.location,
        joining_date=emp.joining_date if show_comp else None,
        weekly_capacity_hours=emp.weekly_capacity_hours,
        availability=emp.availability,
        skills=emp.skills or [],
        phone=u.phone if show_comp else None,
        is_active=u.is_active,
        leave_balance_days=emp.leave_balance_days if show_comp else 0,
        active_projects=active_projects,
        utilization=util,
        salary=emp.salary if show_comp else None,
        salary_currency=emp.salary_currency if show_comp else None,
        created_at=emp.created_at,
    )


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(db: DbDep, user: CurrentUser):
    depts = db.scalars(select(Department).order_by(Department.name)).all()
    return [DepartmentOut.model_validate(d) for d in depts]


@router.get("/roles")
def list_roles(user: CurrentUser):
    return [{"key": k, "label": v} for k, v in ROLE_LABELS.items()]


@router.get("", response_model=list[EmployeeOut])
def list_employees(db: DbDep, user: CurrentUser, q: str | None = None, archived: bool = False):
    stmt = (
        select(Employee)
        .options(selectinload(Employee.user), selectinload(Employee.department))
        .join(User, Employee.user_id == User.id)
        .order_by(User.display_name)
    )
    if archived:
        stmt = stmt.where(Employee.deleted_at.is_not(None))
    else:
        stmt = stmt.where(Employee.deleted_at.is_(None), User.deleted_at.is_(None))
    if q:
        stmt = stmt.where(func.lower(User.display_name).like(f"%{q.lower()}%"))
    return [hydrate(db, e, user) for e in db.scalars(stmt).all()]


@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(employee_id: UUID, db: DbDep, user: CurrentUser):
    emp = db.scalar(
        select(Employee)
        .options(selectinload(Employee.user), selectinload(Employee.department))
        .where(Employee.id == employee_id)
    )
    if not emp:
        raise HTTPException(404, "Employee not found")
    return hydrate(db, emp, user)


@router.post("", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreate, db: DbDep, user: CurrentUser):
    require_founder(user)
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(400, "Email already in use")

    display = payload.display_name or f"{payload.first_name} {payload.last_name}".strip()
    u = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        display_name=display,
        phone=payload.phone,
        role_key=payload.role_key,
        is_active=True,
        is_superadmin=payload.role_key == "founder",
        email_verified=True,
    )
    db.add(u)
    db.flush()
    emp = Employee(
        user_id=u.id,
        department_id=payload.department_id,
        manager_id=payload.manager_id,
        job_title=payload.job_title,
        employment_type=payload.employment_type,
        location=payload.location,
        joining_date=payload.joining_date,
        salary=payload.salary if role_has_permission(user.role_key, Perm.COMPENSATION_WRITE) or user.role_key == "founder" else None,
        salary_currency=payload.salary_currency,
        weekly_capacity_hours=payload.weekly_capacity_hours,
        skills=payload.skills,
    )
    db.add(emp)
    db.flush()
    log_activity(
        db,
        actor=user,
        verb="created",
        entity_type="employee",
        entity_id=emp.id,
        summary=f"{user.display_name} added {display} to Studio Sunny",
    )
    audit(db, user=user, action="employee.create", entity_type="employee", entity_id=emp.id)
    db.commit()
    db.refresh(emp)
    emp.user = u
    return hydrate(db, emp, user)


@router.post("/invite")
def invite_employee(payload: EmployeeInvite, db: DbDep, user: CurrentUser):
    require_founder_or_pm(user)
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(400, "Email already in use")

    display = f"{payload.first_name} {payload.last_name}".strip()
    u = User(
        email=payload.email.lower(),
        hashed_password=hash_password(secrets.token_urlsafe(24)),
        first_name=payload.first_name,
        last_name=payload.last_name,
        display_name=display,
        role_key=payload.role_key,
        is_active=False,
        is_superadmin=payload.role_key == "founder",
        email_verified=False,
        org_id=tenant_id(user),
    )
    db.add(u)
    db.flush()
    emp = Employee(
        user_id=u.id,
        department_id=payload.department_id,
        job_title=payload.job_title,
        employment_type=payload.employment_type,
        location=payload.location,
        org_id=tenant_id(user),
    )
    db.add(emp)
    db.flush()

    raw = secrets.token_urlsafe(32)
    db.add(
        AuthToken(
            user_id=u.id,
            token_hash=hash_token(raw),
            kind="invite",
            expires_at=utcnow() + timedelta(days=7),
            meta={"invited_by": str(user.id)},
        )
    )
    invite_url = f"{settings.frontend_url}/invite?token={raw}"
    send_email(
        u.email,
        "You're invited to Studio Sunny HQ",
        f"Hi {payload.first_name},\n\n{user.display_name} invited you to Studio Sunny HQ.\n\n"
        f"Accept your invite:\n{invite_url}\n\nThis link expires in 7 days.",
    )
    log_activity(
        db,
        actor=user,
        verb="invited",
        entity_type="employee",
        entity_id=emp.id,
        summary=f"{user.display_name} invited {display}",
    )
    audit(db, user=user, action="employee.invite", entity_type="employee", entity_id=emp.id)
    db.commit()
    db.refresh(emp)
    emp.user = u
    out = {"employee": hydrate(db, emp, user), "invite_url": invite_url}
    if settings.environment == "development":
        out["dev_note"] = "Invite also logged to API console (SMTP optional)."
    return out


@router.patch("/{employee_id}", response_model=EmployeeOut)
def update_employee(employee_id: UUID, payload: EmployeeUpdate, db: DbDep, user: CurrentUser):
    is_self = bool(user.employee and user.employee.id == employee_id)
    if not is_founder(user) and not is_self:
        raise not_found("Employee")
    emp = db.get(Employee, employee_id)
    if not emp or emp.deleted_at:
        raise not_found("Employee")
    u = emp.user
    data = payload.model_dump(exclude_unset=True)

    # Non-founder self: cannot escalate role / salary / department / is_active
    if not is_founder(user):
        for locked in ("role_key", "salary", "salary_currency", "department_id", "is_active"):
            data.pop(locked, None)

    user_fields = {"first_name", "last_name", "display_name", "role_key", "phone", "is_active"}
    for k in list(data.keys()):
        if k in user_fields:
            setattr(u, k, data.pop(k))
    if "salary" in data:
        if not is_founder(user):
            data.pop("salary")
            data.pop("salary_currency", None)
        else:
            audit(db, user=user, action="employee.compensation_update", entity_type="employee", entity_id=emp.id)

    for k, v in data.items():
        setattr(emp, k, v)
    db.add(u)
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return hydrate(db, emp, user)


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_employee(employee_id: UUID, db: DbDep, user: CurrentUser):
    """Soft-deactivate employee and revoke all of their sessions (founder only)."""
    from sqlalchemy import update

    from app.models.session import RefreshToken

    require_founder(user)
    emp = db.get(Employee, employee_id)
    if not emp or emp.deleted_at:
        raise not_found("Employee")
    u = emp.user
    if u.id == user.id:
        raise HTTPException(400, "Cannot deactivate your own account")

    emp.deleted_at = utcnow()
    u.is_active = False
    u.deleted_at = utcnow()
    db.add(emp)
    db.add(u)
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == u.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    audit(db, user=user, action="employee.deactivate", entity_type="employee", entity_id=emp.id)
    log_activity(
        db,
        actor=user,
        verb="deactivated",
        entity_type="employee",
        entity_id=emp.id,
        summary=f"{user.display_name} deactivated {u.display_name}",
    )
    db.commit()
    return None
