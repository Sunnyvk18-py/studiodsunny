from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class FileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=260)
    kind: str | None = None
    notes: str | None = None
    project_id: UUID | None = None
    client_id: UUID | None = None


class FileOut(ORMModel):
    id: UUID
    name: str
    original_name: str
    mime_type: str
    size_bytes: int
    kind: str
    notes: str | None = None
    project_id: UUID | None = None
    client_id: UUID | None = None
    uploaded_by_id: UUID
    created_at: datetime
    updated_at: datetime
    project_name: str | None = None
    client_name: str | None = None
    uploader_name: str | None = None
    download_url: str | None = None
