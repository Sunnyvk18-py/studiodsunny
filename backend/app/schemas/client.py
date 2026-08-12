from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel, UserBrief


class ClientCreate(BaseModel):
    business_name: str = Field(min_length=2, max_length=200)
    primary_contact_name: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    email: EmailStr | None = None
    location: str | None = None
    website: str | None = None
    industry: str | None = None
    lead_source: str | None = None
    account_manager_id: UUID | None = None
    status: str = "active"
    notes: str | None = None


class ClientUpdate(BaseModel):
    business_name: str | None = None
    primary_contact_name: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    email: EmailStr | None = None
    location: str | None = None
    website: str | None = None
    industry: str | None = None
    lead_source: str | None = None
    account_manager_id: UUID | None = None
    status: str | None = None
    notes: str | None = None
    onboarding_step: int | None = None
    onboarding_complete: bool | None = None


class ClientOut(ORMModel):
    id: UUID
    business_name: str
    slug: str
    primary_contact_name: str | None
    phone: str | None
    whatsapp: str | None
    email: str | None
    location: str | None
    website: str | None
    industry: str | None
    lead_source: str | None
    account_manager_id: UUID | None
    status: str
    lifetime_value: Decimal
    notes: str | None
    onboarding_step: int
    onboarding_complete: bool
    created_at: datetime
    active_projects: int = 0
    pending_invoices: Decimal | None = None
