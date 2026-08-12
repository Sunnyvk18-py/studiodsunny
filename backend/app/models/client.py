from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin
from app.db.mixins import TenantMixin
from app.db.types import GUID


class Client(TenantMixin, Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "clients"

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid4)
    business_name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    primary_contact_name: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    whatsapp: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    lead_source: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    account_manager_id: Mapped[Optional[UUID]] = mapped_column(GUID, ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True, nullable=False)
    lifetime_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    onboarding_step: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    projects: Mapped[list["Project"]] = relationship(back_populates="client")
