from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin
from app.db.mixins import TenantMixin
from app.db.types import GUID


class User(TenantMixin, Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    role_key: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    totp_secret: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    google_sub: Mapped[Optional[str]] = mapped_column(String(128), unique=True, nullable=True, index=True)

    employee: Mapped[Optional["Employee"]] = relationship(back_populates="user", uselist=False)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
