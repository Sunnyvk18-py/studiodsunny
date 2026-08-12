from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.db.mixins import TenantMixin
from app.db.types import GUID


class Department(TenantMixin, Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_id: Mapped[Optional[UUID]] = mapped_column(GUID, ForeignKey("departments.id"), nullable=True)

    employees: Mapped[list["Employee"]] = relationship(back_populates="department")
