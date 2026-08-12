from decimal import Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select

from app.core.authz import is_founder, require_founder
from app.core.deps import CurrentUser, DbDep
from app.models.client import Client
from app.models.employee import Employee
from app.models.invoice import Invoice
from app.models.lead import Lead
from app.models.project import Project
from app.models.task import Task

router = APIRouter()


class ReportSeriesPoint(BaseModel):
    label: str
    value: float


class ReportsOut(BaseModel):
    revenue_collected: float
    revenue_outstanding: float
    revenue_overdue: float
    invoice_count: int
    paid_count: int
    lead_total: int
    lead_won: int
    lead_conversion_pct: float
    active_projects: int
    at_risk_projects: int
    utilization_pct: int
    active_clients: int
    headcount: int
    open_tasks: int
    invoices_by_status: list[ReportSeriesPoint]
    leads_by_stage: list[ReportSeriesPoint]
    projects_by_health: list[ReportSeriesPoint]


def _money(v) -> float:
    return float(Decimal(v or 0))


@router.get("", response_model=ReportsOut)
def get_reports(db: DbDep, user: CurrentUser):
    require_founder(user)

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
    overdue = db.scalar(
        select(func.coalesce(func.sum(Invoice.amount), 0)).where(
            Invoice.deleted_at.is_(None), Invoice.status == "overdue"
        )
    ) or 0
    invoice_count = db.scalar(select(func.count()).select_from(Invoice).where(Invoice.deleted_at.is_(None))) or 0
    paid_count = db.scalar(
        select(func.count()).select_from(Invoice).where(Invoice.deleted_at.is_(None), Invoice.status == "paid")
    ) or 0

    lead_total = db.scalar(select(func.count()).select_from(Lead).where(Lead.deleted_at.is_(None))) or 0
    lead_won = db.scalar(
        select(func.count()).select_from(Lead).where(Lead.deleted_at.is_(None), Lead.stage == "won")
    ) or 0
    conversion = round((lead_won / lead_total) * 100, 1) if lead_total else 0.0

    active_projects = db.scalar(
        select(func.count()).select_from(Project).where(
            Project.deleted_at.is_(None), Project.status.notin_(["completed", "paused"])
        )
    ) or 0
    at_risk = db.scalar(
        select(func.count()).select_from(Project).where(
            Project.deleted_at.is_(None), Project.health.in_(["at_risk", "critical", "needs_attention"])
        )
    ) or 0
    employees = db.scalar(select(func.count()).select_from(Employee).where(Employee.deleted_at.is_(None))) or 0
    assigned = db.scalar(
        select(func.count()).select_from(Task).where(
            Task.deleted_at.is_(None),
            Task.assignee_id.is_not(None),
            Task.status.notin_(["completed", "backlog"]),
        )
    ) or 0
    utilization = min(100, int((assigned / max(employees * 6, 1)) * 100)) if employees else 0
    active_clients = db.scalar(
        select(func.count()).select_from(Client).where(Client.deleted_at.is_(None), Client.status == "active")
    ) or 0
    open_tasks = db.scalar(
        select(func.count()).select_from(Task).where(
            Task.deleted_at.is_(None), Task.status.notin_(["completed", "backlog"])
        )
    ) or 0

    inv_rows = db.execute(
        select(Invoice.status, func.count()).where(Invoice.deleted_at.is_(None)).group_by(Invoice.status)
    ).all()
    lead_rows = db.execute(
        select(Lead.stage, func.count()).where(Lead.deleted_at.is_(None)).group_by(Lead.stage)
    ).all()
    health_rows = db.execute(
        select(Project.health, func.count()).where(Project.deleted_at.is_(None)).group_by(Project.health)
    ).all()

    return ReportsOut(
        revenue_collected=_money(paid) if show_finance else 0,
        revenue_outstanding=_money(outstanding) if show_finance else 0,
        revenue_overdue=_money(overdue) if show_finance else 0,
        invoice_count=invoice_count if show_finance else 0,
        paid_count=paid_count if show_finance else 0,
        lead_total=lead_total,
        lead_won=lead_won,
        lead_conversion_pct=conversion,
        active_projects=active_projects,
        at_risk_projects=at_risk,
        utilization_pct=utilization,
        active_clients=active_clients,
        headcount=employees,
        open_tasks=open_tasks,
        invoices_by_status=[ReportSeriesPoint(label=s or "unknown", value=float(c)) for s, c in inv_rows]
        if show_finance
        else [],
        leads_by_stage=[ReportSeriesPoint(label=s or "unknown", value=float(c)) for s, c in lead_rows],
        projects_by_health=[ReportSeriesPoint(label=s or "unknown", value=float(c)) for s, c in health_rows],
    )
