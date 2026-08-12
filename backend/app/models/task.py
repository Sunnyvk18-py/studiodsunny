from datetime import date, datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin
from app.db.mixins import TenantMixin
from app.db.types import GUID, JSONType


class Task(TenantMixin, Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "tasks"
    __table_args__ = (Index("ix_tasks_priority_status", "priority", "status"),)

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    project_id: Mapped[Optional[UUID]] = mapped_column(GUID, ForeignKey("projects.id"), nullable=True, index=True)
    assignee_id: Mapped[Optional[UUID]] = mapped_column(GUID, ForeignKey("users.id"), nullable=True, index=True)
    reviewer_id: Mapped[Optional[UUID]] = mapped_column(GUID, ForeignKey("users.id"), nullable=True)
    created_by_id: Mapped[UUID] = mapped_column(GUID, ForeignKey("users.id"), nullable=False)
    parent_id: Mapped[Optional[UUID]] = mapped_column(GUID, ForeignKey("tasks.id"), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium", index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="todo", index=True, nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    estimated_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actual_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tags: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    checklist: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped[Optional["Project"]] = relationship(back_populates="tasks")
    comments: Mapped[list["TaskComment"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )


class TaskComment(TenantMixin, Base, TimestampMixin):
    __tablename__ = "task_comments"

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(GUID, ForeignKey("tasks.id"), nullable=False, index=True)
    author_id: Mapped[UUID] = mapped_column(GUID, ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    task: Mapped["Task"] = relationship(back_populates="comments")
