from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    kind: str = "page"
    status: str = "draft"
    summary: str | None = None
    content: dict | None = None
    project_id: UUID | None = None
    client_id: UUID | None = None


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    kind: str | None = None
    status: str | None = None
    summary: str | None = None
    content: dict | None = None
    project_id: UUID | None = None
    client_id: UUID | None = None
    yjs_state_b64: str | None = None


class DocumentListItem(ORMModel):
    id: UUID
    title: str
    slug: str
    kind: str
    status: str
    summary: str | None = None
    project_id: UUID | None = None
    client_id: UUID | None = None
    created_by_id: UUID
    updated_by_id: UUID | None = None
    updated_at: datetime
    created_at: datetime
    project_name: str | None = None
    client_name: str | None = None
    author_name: str | None = None


class DocumentOut(DocumentListItem):
    content: dict
    plain_text: str | None = None
    has_yjs_state: bool = False


class YjsStateOut(BaseModel):
    yjs_state_b64: str | None = None
