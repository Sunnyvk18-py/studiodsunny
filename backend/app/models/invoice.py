from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin
from app.db.mixins import TenantMixin
from app.db.types import GUID


class Invoice(TenantMixin, Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "invoices"

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid4)
    number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    client_id: Mapped[UUID] = mapped_column(GUID, ForeignKey("clients.id"), nullable=False, index=True)
    project_id: Mapped[Optional[UUID]] = mapped_column(GUID, ForeignKey("projects.id"), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    tax: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    issued_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True, nullable=False)
    payment_method: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
