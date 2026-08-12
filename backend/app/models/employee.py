from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin
from app.db.mixins import TenantMixin
from app.db.types import GUID, JSONType


class Employee(TenantMixin, Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "employees"

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(GUID, ForeignKey("users.id"), unique=True, nullable=False)
    department_id: Mapped[Optional[UUID]] = mapped_column(GUID, ForeignKey("departments.id"), nullable=True)
    manager_id: Mapped[Optional[UUID]] = mapped_column(GUID, ForeignKey("employees.id"), nullable=True)
    job_title: Mapped[str] = mapped_column(String(160), nullable=False)
    employment_type: Mapped[str] = mapped_column(String(40), default="full_time", nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    joining_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    salary: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    salary_currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)
    weekly_capacity_hours: Mapped[int] = mapped_column(Integer, default=40, nullable=False)
    availability: Mapped[str] = mapped_column(String(40), default="available", nullable=False)
    skills: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    leave_balance_days: Mapped[int] = mapped_column(Integer, default=18, nullable=False)

    user: Mapped["User"] = relationship(back_populates="employee")
    department: Mapped[Optional["Department"]] = relationship(back_populates="employees")
