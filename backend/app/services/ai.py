from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.authz import is_founder, is_founder_or_pm, is_project_member, project_member_ids
from app.core.permissions import Perm, role_has_permission
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.lead import Lead
from app.models.project import Project
from app.models.task import Task
from app.models.user import User


def founder_briefing(db: Session, user: User) -> tuple[str, list[str]]:
    member_ids = project_member_ids(db, user.id)
    if is_founder(user) or is_founder_or_pm(user):
        active_projects = db.scalar(
            select(func.count()).select_from(Project).where(
                Project.deleted_at.is_(None),
                Project.status.notin_(["completed", "paused"]),
            )
        ) or 0
    else:
        active_projects = db.scalar(
            select(func.count()).select_from(Project).where(
                Project.deleted_at.is_(None),
                Project.status.notin_(["completed", "paused"]),
                Project.id.in_(member_ids or {None}),
            )
        ) or 0
    at_risk_all = db.scalars(
        select(Project).where(
            Project.deleted_at.is_(None),
            Project.health.in_(["at_risk", "critical", "needs_attention"]),
        )
    ).all()
    at_risk = [
        p
        for p in at_risk_all
        if is_founder(user) or is_founder_or_pm(user) or is_project_member(db, user, p.id)
    ]

    lines = [
        f"Good morning, {user.first_name}.",
        f"Studio Sunny currently has {active_projects} active project{'s' if active_projects != 1 else ''}.",
    ]
    if at_risk:
        lines.append(f"{len(at_risk)} project{'s' if len(at_risk) != 1 else ''} require attention.")
        for p in at_risk[:3]:
            if p.health == "at_risk":
                lines.append(f"{p.name} is approaching a critical deadline.")
            elif p.health == "needs_attention":
                lines.append(f"{p.name} is waiting on a blocker.")
            else:
                lines.append(f"{p.name} is in critical status.")
    outstanding = 0
    if is_founder(user):
        outstanding = db.scalar(
            select(func.coalesce(func.sum(Invoice.amount), 0)).where(
                Invoice.deleted_at.is_(None),
                Invoice.status.in_(["sent", "viewed", "partial", "overdue"]),
            )
        ) or 0
        if outstanding:
            lines.append(f"₹{int(outstanding):,} in invoices remain outstanding.")

    actions: list[str] = []
    for p in at_risk[:2]:
        actions.append(f"Review {p.name}.")
    if outstanding:
        actions.append("Follow up on outstanding invoices.")
    if not actions:
        actions.append("Scan My Desk and clear today's focus list.")

    return "\n\n".join(lines), actions


def answer_question(db: Session, user: User, question: str) -> tuple[str, list[str]]:
    q = question.lower().strip()
    citations: list[str] = []
    member_ids = project_member_ids(db, user.id)

    if any(w in q for w in ["salary", "compensation", "payroll", "pay someone"]):
        if not role_has_permission(user.role_key, Perm.COMPENSATION_READ):
            return (
                "I can’t share compensation or salary information with your current role.",
                [],
            )

    if "focus" in q or "today" in q:
        tasks = db.scalars(
            select(Task)
            .where(
                Task.assignee_id == user.id,
                Task.deleted_at.is_(None),
                Task.status.notin_(["completed", "backlog"]),
            )
            .order_by(Task.due_date.asc())
            .limit(5)
        ).all()
        if not tasks:
            return ("Your plate looks clear. No open tasks are assigned to you.", [])
        lines = ["Here’s what I’d focus on:"]
        for i, t in enumerate(tasks, 1):
            lines.append(f"{i}. {t.title} ({t.priority}, {t.status.replace('_', ' ')})")
        return "\n".join(lines), ["My Desk"]

    if "behind" in q or "at risk" in q or "attention" in q:
        projects = db.scalars(
            select(Project).where(
                Project.deleted_at.is_(None),
                Project.health.in_(["at_risk", "critical", "needs_attention"]),
            )
        ).all()
        projects = [p for p in projects if is_founder(user) or is_project_member(db, user, p.id) or p.id in member_ids]
        if not projects:
            return ("No projects are currently flagged as behind or at risk.", ["Projects"])
        lines = ["Projects needing attention:"]
        for p in projects:
            lines.append(f"• {p.name} — {p.health.replace('_', ' ')} · {p.progress}% · {p.status.replace('_', ' ')}")
        return "\n".join(lines), [p.name for p in projects]

    if "haven't paid" in q or "outstanding" in q or "overdue" in q or "invoices" in q:
        if not is_founder(user):
            return ("Invoice and payment data is restricted to finance and leadership.", [])
        invoices = db.scalars(
            select(Invoice).where(
                Invoice.deleted_at.is_(None),
                Invoice.status.in_(["sent", "viewed", "partial", "overdue"]),
            )
        ).all()
        if not invoices:
            return ("No outstanding invoices right now.", ["Finance"])
        total = sum((i.amount for i in invoices), start=0)
        lines = [f"{len(invoices)} invoices outstanding · ₹{int(total):,}"]
        for inv in invoices:
            client = db.get(Client, inv.client_id)
            lines.append(f"• {inv.number} — {client.business_name if client else 'Client'} · ₹{int(inv.amount):,} ({inv.status})")
        return "\n".join(lines), ["Finance"]

    if "urgent" in q:
        tasks = db.scalars(
            select(Task).where(
                Task.deleted_at.is_(None),
                Task.priority == "urgent",
                Task.status.notin_(["completed"]),
            ).limit(20)
        ).all()
        if is_founder(user):
            pass
        else:
            tasks = [
                t
                for t in tasks
                if t.assignee_id == user.id or is_project_member(db, user, t.project_id)
            ]
        if not tasks:
            return ("No urgent open tasks.", [])
        return "Urgent tasks:\n" + "\n".join(f"• {t.title}" for t in tasks), []

    if "availability" in q or "who has" in q or "capacity" in q:
        from app.models.employee import Employee

        employees = db.scalars(select(Employee).where(Employee.deleted_at.is_(None))).all()
        lines = ["Team availability:"]
        for emp in employees:
            u = db.get(User, emp.user_id)
            assigned = db.scalar(
                select(func.count()).select_from(Task).where(
                    Task.assignee_id == emp.user_id,
                    Task.deleted_at.is_(None),
                    Task.status.notin_(["completed", "backlog"]),
                )
            ) or 0
            util = min(100, int((assigned / 6) * 100)) if assigned else 12
            lines.append(f"• {u.display_name if u else 'Employee'} — {emp.availability}, ~{util}% utilized")
        return "\n".join(lines), ["Team"]

    if "lead" in q or "pipeline" in q:
        if not is_founder_or_pm(user):
            return ("Lead pipeline access is limited for your role.", [])
        count = db.scalar(select(func.count()).select_from(Lead).where(Lead.deleted_at.is_(None))) or 0
        return (f"There are {count} open leads in the pipeline.", ["Leads"])

    # project name lookup — only projects the caller can see
    projects = db.scalars(select(Project).where(Project.deleted_at.is_(None))).all()
    for p in projects:
        if p.name.lower() in q or p.slug.replace("-", " ") in q:
            if not (is_founder(user) or is_founder_or_pm(user) or is_project_member(db, user, p.id)):
                continue
            open_tasks = db.scalar(
                select(func.count()).select_from(Task).where(
                    Task.project_id == p.id,
                    Task.deleted_at.is_(None),
                    Task.status.notin_(["completed"]),
                )
            ) or 0
            client_name = "—"
            if is_founder_or_pm(user):
                client = db.get(Client, p.client_id)
                client_name = client.business_name if client else "—"
            answer = (
                f"{p.name} is in {p.status.replace('_', ' ')} with {p.progress}% complete. "
                f"Health: {p.health.replace('_', ' ')}. "
                f"Client: {client_name}. "
                f"{open_tasks} open tasks remain."
            )
            if p.target_completion_date:
                answer += f" Target: {p.target_completion_date.isoformat()}."
            return answer, [p.name]

    if "briefing" in q or "summary" in q or "yesterday" in q or "what changed" in q:
        text, _ = founder_briefing(db, user)
        return text, ["Home"]

    return (
        "I can help with project status, focus for today, at-risk work, team availability, "
        "urgent tasks, and (if you’re authorized) invoices. Try asking about a project you’re on.",
        [],
    )
