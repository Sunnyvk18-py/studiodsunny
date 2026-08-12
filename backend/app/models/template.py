from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base, SoftDeleteMixin, TimestampMixin
from app.db.mixins import TenantMixin
from app.db.types import GUID


class Template(TenantMixin, Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "templates"

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(String(40), nullable=False, index=True)  # project | task | onboarding | doc
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_by_id: Mapped[UUID | None] = mapped_column(GUID, ForeignKey("users.id"), nullable=True)
