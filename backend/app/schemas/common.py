from datetime import date, datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserBrief(ORMModel):
    id: UUID
    display_name: str
    email: str
    role_key: str
    avatar_url: str | None = None


class Paginated(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int = 1
    page_size: int = 50


class Message(BaseModel):
    message: str


class IdName(ORMModel):
    id: UUID
    name: str
