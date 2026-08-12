from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.db.mixins import TenantMixin
from app.db.types import GUID


class Notification(TenantMixin, Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(GUID, ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    entity_id: Mapped[Optional[UUID]] = mapped_column(GUID, nullable=True)
    href: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="normal", nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
