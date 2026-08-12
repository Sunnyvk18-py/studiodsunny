from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMModel, UserBrief


class ActivityOut(ORMModel):
    id: UUID
    actor_id: UUID | None
    verb: str
    entity_type: str
    entity_id: UUID | None
    project_id: UUID | None
    client_id: UUID | None
    summary: str
    meta: dict
    created_at: datetime
    actor: UserBrief | None = None


class NotificationOut(ORMModel):
    id: UUID
    user_id: UUID
    type: str
    title: str
    body: str
    entity_type: str | None
    entity_id: UUID | None
    href: str | None
    priority: str
    read_at: datetime | None
    created_at: datetime


class InvoiceOut(ORMModel):
    id: UUID
    number: str
    client_id: UUID
    project_id: UUID | None
    amount: Decimal
    tax: Decimal
    discount: Decimal
    currency: str
    due_date: date | None
    status: str
    payment_method: str | None
    notes: str | None
    client_name: str | None = None


class LeadOut(ORMModel):
    id: UUID
    business_name: str
    contact_name: str | None
    phone: str | None
    email: str | None
    industry: str | None
    location: str | None
    requested_service: str | None
    estimated_value: Decimal
    currency: str
    source: str | None
    stage: str
    assigned_to_id: UUID | None
    probability: int
    notes: str | None


class KpiCard(BaseModel):
    key: str
    label: str
    value: str | int | float
    delta: float | None = None
    delta_label: str | None = None
    tone: str = "neutral"
    hint: str | None = None


class AttentionItem(BaseModel):
    severity: str
    title: str
    href: str | None = None


class DashboardOut(BaseModel):
    greeting_name: str
    kpis: list[KpiCard]
    attention: list[AttentionItem]
    activity: list[ActivityOut]
    briefing: str
    recommended_actions: list[str]
    health: dict


class DeskOut(BaseModel):
    focus: list
    due_today: list
    upcoming: list
    blocked: list
    projects: list
    notifications: list[NotificationOut]
    activity: list[ActivityOut]


class SearchHit(BaseModel):
    type: str
    id: UUID
    title: str
    subtitle: str | None = None
    href: str


class SearchOut(BaseModel):
    results: list[SearchHit]


class AIAskRequest(BaseModel):
    question: str


class AIAskResponse(BaseModel):
    answer: str
    citations: list[str] = []
