from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.db.mixins import TenantMixin
from app.db.types import GUID


class RefreshToken(TenantMixin, Base, TimestampMixin):
    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(GUID, ForeignKey("users.id"), index=True, nullable=False)
    family_id: Mapped[UUID] = mapped_column(GUID, index=True, nullable=False, default=uuid4)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_id: Mapped[Optional[UUID]] = mapped_column(GUID, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
