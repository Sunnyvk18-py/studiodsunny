from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, utcnow
from app.db.mixins import TenantMixin
from app.db.types import GUID


class ChatChannel(TenantMixin, Base, TimestampMixin):
    __tablename__ = "chat_channels"

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), default="channel", nullable=False)
    topic: Mapped[Optional[str]] = mapped_column(String(280), nullable=True)

    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="channel")
    members: Mapped[list["ChatChannelMember"]] = relationship(
        back_populates="channel", cascade="all, delete-orphan"
    )


class ChatChannelMember(TenantMixin, Base, TimestampMixin):
    __tablename__ = "chat_channel_members"
    __table_args__ = (UniqueConstraint("channel_id", "user_id", name="uq_chat_channel_member"),)

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid4)
    channel_id: Mapped[UUID] = mapped_column(GUID, ForeignKey("chat_channels.id"), index=True, nullable=False)
    user_id: Mapped[UUID] = mapped_column(GUID, ForeignKey("users.id"), index=True, nullable=False)

    channel: Mapped[ChatChannel] = relationship(back_populates="members")


class ChatMessage(TenantMixin, Base):
    __tablename__ = "chat_messages"

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid4)
    channel_id: Mapped[UUID] = mapped_column(GUID, ForeignKey("chat_channels.id"), index=True, nullable=False)
    author_id: Mapped[UUID] = mapped_column(GUID, ForeignKey("users.id"), index=True, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True, nullable=False)

    channel: Mapped[ChatChannel] = relationship(back_populates="messages")
