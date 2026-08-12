from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin
from app.db.mixins import TenantMixin
from app.db.types import GUID


class Lead(TenantMixin, Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "leads"

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid4)
    business_name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_name: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    whatsapp: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    requested_service: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    estimated_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    stage: Mapped[str] = mapped_column(String(40), default="new_lead", index=True, nullable=False)
    assigned_to_id: Mapped[Optional[UUID]] = mapped_column(GUID, ForeignKey("users.id"), nullable=True)
    next_follow_up: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    probability: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    converted_client_id: Mapped[Optional[UUID]] = mapped_column(GUID, ForeignKey("clients.id"), nullable=True)
