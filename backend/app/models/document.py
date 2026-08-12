from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin
from app.db.mixins import TenantMixin
from app.db.types import GUID, JSONType

EMPTY_DOC = {"type": "doc", "content": [{"type": "paragraph"}]}


class Document(TenantMixin, Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    slug: Mapped[str] = mapped_column(String(260), unique=True, index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(40), default="page", index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    content: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    plain_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    yjs_state: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    project_id: Mapped[Optional[UUID]] = mapped_column(GUID, ForeignKey("projects.id"), nullable=True, index=True)
    client_id: Mapped[Optional[UUID]] = mapped_column(GUID, ForeignKey("clients.id"), nullable=True, index=True)
    created_by_id: Mapped[UUID] = mapped_column(GUID, ForeignKey("users.id"), nullable=False)
    updated_by_id: Mapped[Optional[UUID]] = mapped_column(GUID, ForeignKey("users.id"), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
