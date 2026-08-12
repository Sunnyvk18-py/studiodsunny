from contextvars import ContextVar
from enum import StrEnum

# Additive org-level extras, set per-request in get_current_user
_perm_overrides: ContextVar[dict | None] = ContextVar("perm_overrides", default=None)


def set_permission_overrides(overrides: dict | None) -> None:
    _perm_overrides.set(overrides or {})


def get_permission_overrides() -> dict:
    return _perm_overrides.get() or {}



class Role(StrEnum):
    FOUNDER = "founder"
    OPERATIONS_MANAGER = "operations_manager"
    PROJECT_MANAGER = "project_manager"
    DEVELOPER = "developer"
    DESIGNER = "designer"
    AUTOMATION_ENGINEER = "automation_engineer"
    MARKETING = "marketing"
    SALES = "sales"
    FINANCE = "finance"
    FREELANCER = "freelancer"


class Perm(StrEnum):
    ALL = "*"

    CLIENTS_READ = "clients:read"
    CLIENTS_WRITE = "clients:write"

    PROJECTS_READ = "projects:read"
    PROJECTS_WRITE = "projects:write"
    PROJECTS_DELETE = "projects:delete"

    TASKS_READ = "tasks:read"
    TASKS_WRITE = "tasks:write"

    EMPLOYEES_READ = "employees:read"
    EMPLOYEES_WRITE = "employees:write"
    COMPENSATION_READ = "employees.compensation:read"
    COMPENSATION_WRITE = "employees.compensation:write"

    LEADS_READ = "leads:read"
    LEADS_WRITE = "leads:write"

    FINANCE_READ = "finance:read"
    FINANCE_WRITE = "finance:write"

    CREDENTIALS_READ = "credentials:read"
    CREDENTIALS_WRITE = "credentials:write"

    FILES_READ = "files:read"
    FILES_WRITE = "files:write"

    MESSAGES_READ = "messages:read"
    MESSAGES_WRITE = "messages:write"

    REPORTS_READ = "reports:read"
    AUDIT_READ = "audit:read"

    SETTINGS_WRITE = "settings:write"
    DEPARTMENTS_WRITE = "departments:write"
    PERMISSIONS_WRITE = "permissions:write"

    ATTENDANCE_READ = "attendance:read"
    ATTENDANCE_MANAGE = "attendance:manage"
    LEAVE_MANAGE = "leave:manage"

    AI_USE = "ai:use"


ROLE_LABELS: dict[str, str] = {
    Role.FOUNDER: "Founder",
    Role.OPERATIONS_MANAGER: "Operations Manager",
    Role.PROJECT_MANAGER: "Project Manager",
    Role.DEVELOPER: "Developer",
    Role.DESIGNER: "Designer",
    Role.AUTOMATION_ENGINEER: "Automation Engineer",
    Role.MARKETING: "Marketing / SEO",
    Role.SALES: "Sales",
    Role.FINANCE: "Finance",
    Role.FREELANCER: "Freelancer",
}

_COMMON = [
    Perm.PROJECTS_READ,
    Perm.TASKS_READ,
    Perm.TASKS_WRITE,
    Perm.FILES_READ,
    Perm.MESSAGES_READ,
    Perm.MESSAGES_WRITE,
    Perm.AI_USE,
]

ROLE_PERMISSIONS: dict[str, list[str]] = {
    Role.FOUNDER: [Perm.ALL],
    Role.OPERATIONS_MANAGER: [
        *_COMMON,
        Perm.CLIENTS_READ,
        Perm.CLIENTS_WRITE,
        Perm.PROJECTS_WRITE,
        Perm.EMPLOYEES_READ,
        Perm.LEADS_READ,
        Perm.LEADS_WRITE,
        Perm.FILES_WRITE,
        Perm.REPORTS_READ,
        Perm.ATTENDANCE_READ,
        Perm.LEAVE_MANAGE,
        Perm.DEPARTMENTS_WRITE,
    ],
    Role.PROJECT_MANAGER: [
        *_COMMON,
        Perm.CLIENTS_READ,
        Perm.PROJECTS_WRITE,
        Perm.EMPLOYEES_READ,
        Perm.FILES_WRITE,
        Perm.LEAVE_MANAGE,
    ],
    Role.DEVELOPER: [*_COMMON, Perm.FILES_WRITE],
    Role.DESIGNER: [*_COMMON, Perm.FILES_WRITE],
    Role.AUTOMATION_ENGINEER: [*_COMMON, Perm.FILES_WRITE],
    Role.MARKETING: [
        *_COMMON,
        Perm.CLIENTS_READ,
        Perm.LEADS_READ,
        Perm.FILES_WRITE,
    ],
    Role.SALES: [
        *_COMMON,
        Perm.CLIENTS_READ,
        Perm.CLIENTS_WRITE,
        Perm.LEADS_READ,
        Perm.LEADS_WRITE,
        Perm.PROJECTS_WRITE,
        Perm.FILES_WRITE,
    ],
    Role.FINANCE: [
        *_COMMON,
        Perm.CLIENTS_READ,
        Perm.FINANCE_READ,
        Perm.FINANCE_WRITE,
        Perm.REPORTS_READ,
        Perm.EMPLOYEES_READ,
        Perm.COMPENSATION_READ,
    ],
    Role.FREELANCER: [
        Perm.PROJECTS_READ,
        Perm.TASKS_READ,
        Perm.TASKS_WRITE,
        Perm.FILES_READ,
        Perm.MESSAGES_READ,
        Perm.AI_USE,
    ],
}

SENSITIVE_PERMS = {
    Perm.COMPENSATION_READ,
    Perm.COMPENSATION_WRITE,
    Perm.FINANCE_READ,
    Perm.FINANCE_WRITE,
    Perm.CREDENTIALS_READ,
    Perm.CREDENTIALS_WRITE,
    Perm.AUDIT_READ,
}


def role_has_permission(role: str, permission: str) -> bool:
    granted = ROLE_PERMISSIONS.get(role, [])
    if Perm.ALL in granted or "*" in granted:
        return True
    if permission in granted:
        return True
    extras = get_permission_overrides().get(role) or []
    return permission in extras


def permissions_for_role(role: str) -> list[str]:
    granted = ROLE_PERMISSIONS.get(role, [])
    if Perm.ALL in granted:
        base = [p.value if isinstance(p, Perm) else p for p in Perm]
    else:
        base = [p.value if isinstance(p, Perm) else p for p in granted]
    extras = get_permission_overrides().get(role) or []
    for e in extras:
        if e not in base:
            base.append(e)
    return base


def permission_matrix() -> dict:
    """Full role → permissions map for admin UI."""
    out: dict[str, list[str]] = {}
    for role in Role:
        out[role.value] = permissions_for_role(role.value)
    all_perms = sorted({p.value for p in Perm if p != Perm.ALL})
    return {"roles": out, "all_permissions": all_perms, "labels": dict(ROLE_LABELS), "overrides": get_permission_overrides()}
