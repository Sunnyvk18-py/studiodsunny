from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin
from app.db.mixins import TenantMixin
from app.db.types import GUID


class FileAsset(TenantMixin, Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "file_assets"

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(260), nullable=False)
    original_name: Mapped[str] = mapped_column(String(260), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(420), unique=True, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), default="application/octet-stream", nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    kind: Mapped[str] = mapped_column(String(40), default="asset", index=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    project_id: Mapped[Optional[UUID]] = mapped_column(GUID, ForeignKey("projects.id"), nullable=True, index=True)
    client_id: Mapped[Optional[UUID]] = mapped_column(GUID, ForeignKey("clients.id"), nullable=True, index=True)
    uploaded_by_id: Mapped[UUID] = mapped_column(GUID, ForeignKey("users.id"), nullable=False, index=True)
