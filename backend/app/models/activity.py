from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.db.mixins import TenantMixin
from app.db.types import GUID, JSONType


class Activity(TenantMixin, Base, TimestampMixin):
    __tablename__ = "activities"

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid4)
    actor_id: Mapped[Optional[UUID]] = mapped_column(GUID, ForeignKey("users.id"), nullable=True, index=True)
    verb: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[Optional[UUID]] = mapped_column(GUID, nullable=True)
    project_id: Mapped[Optional[UUID]] = mapped_column(GUID, ForeignKey("projects.id"), nullable=True, index=True)
    client_id: Mapped[Optional[UUID]] = mapped_column(GUID, ForeignKey("clients.id"), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
