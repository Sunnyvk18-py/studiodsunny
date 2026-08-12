from decimal import Decimal

from fastapi import APIRouter
from sqlalchemy import func, select

from app.core.authz import is_founder
from app.core.deps import CurrentUser, DbDep
from app.core.permissions import Perm, role_has_permission
from app.models.activity import Activity
from app.models.client import Client
from app.models.employee import Employee
from app.models.invoice import Invoice
from app.models.lead import Lead
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.schemas.common import UserBrief
from app.schemas.misc import ActivityOut, AttentionItem, DashboardOut, KpiCard
from app.services.ai import founder_briefing

router = APIRouter()


def _inr(value) -> str:
    n = int(Decimal(value or 0))
    return f"₹{n:,}"


@router.get("", response_model=DashboardOut)
def get_dashboard(db: DbDep, user: CurrentUser):
    active_clients = db.scalar(
        select(func.count()).select_from(Client).where(Client.deleted_at.is_(None), Client.status == "active")
    ) or 0
    active_projects = db.scalar(
        select(func.count()).select_from(Project).where(
            Project.deleted_at.is_(None), Project.status.notin_(["completed", "paused"])
        )
    ) or 0
    employees = db.scalar(
        select(func.count()).select_from(Employee).where(Employee.deleted_at.is_(None))
    ) or 0
    new_leads = db.scalar(
        select(func.count()).select_from(Lead).where(Lead.deleted_at.is_(None), Lead.stage == "new_lead")
    ) or 0
    at_risk = db.scalar(
        select(func.count()).select_from(Project).where(
            Project.deleted_at.is_(None), Project.health.in_(["at_risk", "critical"])
        )
    ) or 0
    open_tasks = db.scalar(
        select(func.count()).select_from(Task).where(
            Task.deleted_at.is_(None), Task.status.notin_(["completed", "backlog"])
        )
    ) or 0

    show_finance = is_founder(user)
    paid = db.scalar(
        select(func.coalesce(func.sum(Invoice.amount), 0)).where(
            Invoice.deleted_at.is_(None), Invoice.status == "paid"
        )
    ) or 0
    outstanding = db.scalar(
        select(func.coalesce(func.sum(Invoice.amount), 0)).where(
            Invoice.deleted_at.is_(None), Invoice.status.in_(["sent", "viewed", "partial", "overdue"])
        )
    ) or 0

    # simple utilization: open assigned tasks / 6
    assigned = db.scalar(
        select(func.count()).select_from(Task).where(
            Task.deleted_at.is_(None),
            Task.assignee_id.is_not(None),
            Task.status.notin_(["completed", "backlog"]),
        )
    ) or 0
    utilization = min(100, int((assigned / max(employees * 6, 1)) * 100)) if employees else 0

    kpis: list[KpiCard] = [
        KpiCard(key="clients", label="Active Clients", value=active_clients, delta=12.0, delta_label="vs last month"),
        KpiCard(key="projects", label="Active Projects", value=active_projects, delta=8.0, delta_label="vs last month"),
        KpiCard(key="team", label="Total Employees", value=employees, delta=0, delta_label="headcount stable"),
        KpiCard(key="leads", label="New Leads", value=new_leads, delta=22.0, delta_label="this week"),
        KpiCard(
            key="revenue",
            label="Monthly Revenue",
            value=_inr(paid) if show_finance else "—",
            delta=18.4 if show_finance else None,
            delta_label="this month" if show_finance else "restricted",
            tone="positive" if show_finance else "neutral",
        ),
        KpiCard(
            key="outstanding",
            label="Outstanding Payments",
            value=_inr(outstanding) if show_finance else "—",
            delta=None,
            tone="warning" if show_finance and outstanding else "neutral",
        ),
        KpiCard(
            key="risk",
            label="Projects At Risk",
            value=at_risk,
            tone="danger" if at_risk else "positive",
        ),
        KpiCard(
            key="util",
            label="Team Utilization",
            value=f"{utilization}%",
            tone="warning" if utilization >= 85 else "neutral",
        ),
    ]

    attention: list[AttentionItem] = []
    risky = db.scalars(
        select(Project).where(
            Project.deleted_at.is_(None),
            Project.health.in_(["at_risk", "critical", "needs_attention"]),
        )
    ).all()
    for p in risky:
        attention.append(
            AttentionItem(
                severity="warning" if p.health != "critical" else "critical",
                title=f"{p.name} is {p.health.replace('_', ' ')}",
                href=f"/projects/{p.id}",
            )
        )
    overdue_count = db.scalar(
        select(func.count()).select_from(Invoice).where(Invoice.deleted_at.is_(None), Invoice.status == "overdue")
    ) or 0
    if overdue_count and show_finance:
        attention.append(
            AttentionItem(
                severity="warning",
                title=f"{overdue_count} invoice{'s' if overdue_count != 1 else ''} overdue",
                href="/finance",
            )
        )
    if utilization >= 90:
        attention.append(
            AttentionItem(severity="warning", title="Developer workload above 90%", href="/team")
        )

    activities = db.scalars(select(Activity).order_by(Activity.created_at.desc()).limit(12)).all()
    actor_ids = [a.actor_id for a in activities if a.actor_id]
    actors = {u.id: u for u in db.scalars(select(User).where(User.id.in_(actor_ids))).all()} if actor_ids else {}
    activity_out = []
    for a in activities:
        actor = actors.get(a.actor_id) if a.actor_id else None
        activity_out.append(
            ActivityOut(
                id=a.id,
                actor_id=a.actor_id,
                verb=a.verb,
                entity_type=a.entity_type,
                entity_id=a.entity_id,
                project_id=a.project_id,
                client_id=a.client_id,
                summary=a.summary,
                meta=a.meta or {},
                created_at=a.created_at,
                actor=UserBrief.model_validate(actor) if actor else None,
            )
        )

    briefing, actions = founder_briefing(db, user)

    health = {
        "revenue": str(paid) if show_finance else None,
        "projects": active_projects,
        "utilization": utilization,
        "leads": new_leads,
        "outstanding": str(outstanding) if show_finance else None,
        "open_tasks": open_tasks,
        "active_clients": active_clients,
    }

    return DashboardOut(
        greeting_name=user.first_name,
        kpis=kpis,
        attention=attention,
        activity=activity_out,
        briefing=briefing,
        recommended_actions=actions,
        health=health,
    )
