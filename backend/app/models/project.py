from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin
from app.db.mixins import TenantMixin
from app.db.types import GUID, JSONType


class Project(TenantMixin, Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    client_id: Mapped[UUID] = mapped_column(GUID, ForeignKey("clients.id"), nullable=False, index=True)
    project_manager_id: Mapped[Optional[UUID]] = mapped_column(GUID, ForeignKey("users.id"), nullable=True)
    project_type: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    target_completion_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    budget: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    budget_currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="planning", index=True, nullable=False)
    health: Mapped[str] = mapped_column(String(40), default="healthy", index=True, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tech_stack: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    repository_url: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    production_url: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    staging_url: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    hours_spent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    client: Mapped["Client"] = relationship(back_populates="projects")
    members: Mapped[list["ProjectMember"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    milestones: Mapped[list["ProjectMilestone"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["Task"]] = relationship(back_populates="project")


class ProjectMember(TenantMixin, Base, TimestampMixin):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_member"),)

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(GUID, ForeignKey("projects.id"), nullable=False, index=True)
    user_id: Mapped[UUID] = mapped_column(GUID, ForeignKey("users.id"), nullable=False, index=True)
    role_on_project: Mapped[str] = mapped_column(String(80), default="contributor", nullable=False)

    project: Mapped["Project"] = relationship(back_populates="members")


class ProjectMilestone(TenantMixin, Base, TimestampMixin):
    __tablename__ = "project_milestones"

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(GUID, ForeignKey("projects.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    phase: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[Optional[UUID]] = mapped_column(GUID, ForeignKey("users.id"), nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="upcoming", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deliverables: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)

    project: Mapped["Project"] = relationship(back_populates="milestones")
