from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel, UserBrief


PROJECT_TYPES = [
    "Website",
    "E-commerce",
    "Mobile App",
    "AI Automation",
    "WhatsApp Automation",
    "Custom Software",
    "SEO",
    "Digital Transformation",
    "Other",
]

PROJECT_STATUSES = [
    "planning",
    "design",
    "development",
    "testing",
    "client_review",
    "launching",
    "maintenance",
    "completed",
    "paused",
]

PROJECT_HEALTH = ["healthy", "needs_attention", "at_risk", "critical"]
PROJECT_PRIORITIES = ["low", "medium", "high", "urgent"]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    client_id: UUID
    project_type: str
    description: str | None = None
    project_manager_id: UUID | None = None
    start_date: date | None = None
    target_completion_date: date | None = None
    budget: Decimal | None = None
    budget_currency: str = "INR"
    priority: str = "medium"
    tech_stack: list[str] = Field(default_factory=list)
    repository_url: str | None = None
    production_url: str | None = None
    staging_url: str | None = None
    member_ids: list[UUID] = Field(default_factory=list)


class ProjectUpdate(BaseModel):
    name: str | None = None
    project_type: str | None = None
    description: str | None = None
    project_manager_id: UUID | None = None
    start_date: date | None = None
    target_completion_date: date | None = None
    budget: Decimal | None = None
    budget_currency: str | None = None
    status: str | None = None
    health: str | None = None
    priority: str | None = None
    tech_stack: list[str] | None = None
    repository_url: str | None = None
    production_url: str | None = None
    staging_url: str | None = None
    is_pinned: bool | None = None
    member_ids: list[UUID] | None = None


class MilestoneCreate(BaseModel):
    title: str
    phase: str
    description: str | None = None
    owner_id: UUID | None = None
    start_date: date | None = None
    due_date: date | None = None
    status: str = "upcoming"
    sort_order: int = 0
    deliverables: list[str] = Field(default_factory=list)


class MilestoneOut(ORMModel):
    id: UUID
    project_id: UUID
    title: str
    phase: str
    description: str | None
    owner_id: UUID | None
    start_date: date | None
    due_date: date | None
    status: str
    sort_order: int
    deliverables: list


class ProjectMemberOut(ORMModel):
    id: UUID
    user_id: UUID
    role_on_project: str
    user: UserBrief | None = None


class ProjectOut(ORMModel):
    id: UUID
    name: str
    slug: str
    client_id: UUID
    project_manager_id: UUID | None
    project_type: str
    description: str | None
    start_date: date | None
    target_completion_date: date | None
    budget: Decimal | None
    budget_currency: str
    status: str
    health: str
    priority: str
    progress: int
    tech_stack: list
    repository_url: str | None
    production_url: str | None
    staging_url: str | None
    hours_spent: int
    is_pinned: bool
    created_at: datetime
    client_name: str | None = None
    manager_name: str | None = None
    team_count: int = 0
    open_tasks: int = 0
    blocked_tasks: int = 0
    archived: bool = False


class ProjectDetail(ProjectOut):
    members: list[ProjectMemberOut] = []
    milestones: list[MilestoneOut] = []
