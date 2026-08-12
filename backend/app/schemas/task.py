from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel, UserBrief


TASK_STATUSES = ["backlog", "todo", "in_progress", "review", "blocked", "completed"]
TASK_PRIORITIES = ["low", "medium", "high", "urgent"]


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str | None = None
    project_id: UUID | None = None
    assignee_id: UUID | None = None
    reviewer_id: UUID | None = None
    priority: str = "medium"
    status: str = "todo"
    due_date: date | None = None
    start_date: date | None = None
    estimated_minutes: int | None = None
    tags: list[str] = Field(default_factory=list)
    checklist: list[dict] = Field(default_factory=list)
    parent_id: UUID | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    project_id: UUID | None = None
    assignee_id: UUID | None = None
    reviewer_id: UUID | None = None
    priority: str | None = None
    status: str | None = None
    due_date: date | None = None
    start_date: date | None = None
    estimated_minutes: int | None = None
    actual_minutes: int | None = None
    tags: list[str] | None = None
    checklist: list[dict] | None = None


class TaskCommentCreate(BaseModel):
    body: str = Field(min_length=1)


class TaskCommentUpdate(BaseModel):
    body: str = Field(min_length=1)


class TaskCommentOut(ORMModel):
    id: UUID
    task_id: UUID
    author_id: UUID
    body: str
    created_at: datetime
    author: UserBrief | None = None


class TaskOut(ORMModel):
    id: UUID
    title: str
    description: str | None
    project_id: UUID | None
    assignee_id: UUID | None
    reviewer_id: UUID | None
    created_by_id: UUID
    parent_id: UUID | None
    priority: str
    status: str
    due_date: date | None
    start_date: date | None
    estimated_minutes: int | None
    actual_minutes: int | None
    tags: list
    checklist: list
    sort_order: int
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    project_name: str | None = None
    assignee_name: str | None = None
    reviewer_name: str | None = None
