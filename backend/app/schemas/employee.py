from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class EmployeeCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    first_name: str
    last_name: str = ""
    display_name: str | None = None
    role_key: str
    job_title: str
    department_id: UUID | None = None
    manager_id: UUID | None = None
    employment_type: str = "full_time"
    location: str | None = None
    joining_date: date | None = None
    salary: Decimal | None = None
    salary_currency: str = "INR"
    weekly_capacity_hours: int = 40
    skills: list[str] = Field(default_factory=list)
    phone: str | None = None


class EmployeeInvite(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str = ""
    role_key: str
    job_title: str
    department_id: UUID | None = None
    location: str | None = "Hyderabad"
    employment_type: str = "full_time"


class EmployeeUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    role_key: str | None = None
    job_title: str | None = None
    department_id: UUID | None = None
    manager_id: UUID | None = None
    employment_type: str | None = None
    location: str | None = None
    joining_date: date | None = None
    salary: Decimal | None = None
    salary_currency: str | None = None
    weekly_capacity_hours: int | None = None
    availability: str | None = None
    skills: list[str] | None = None
    phone: str | None = None
    is_active: bool | None = None
    leave_balance_days: int | None = None


class DepartmentOut(ORMModel):
    id: UUID
    name: str
    slug: str
    description: str | None
    parent_id: UUID | None


class EmployeeOut(ORMModel):
    id: UUID
    user_id: UUID
    display_name: str
    email: str
    first_name: str
    last_name: str
    avatar_url: str | None
    role_key: str
    job_title: str
    department_id: UUID | None
    department_name: str | None = None
    manager_id: UUID | None
    employment_type: str
    location: str | None
    joining_date: date | None = None
    weekly_capacity_hours: int
    availability: str
    skills: list
    phone: str | None = None
    is_active: bool
    leave_balance_days: int
    active_projects: int = 0
    utilization: int = 0
    salary: Decimal | None = None
    salary_currency: str | None = None
    created_at: datetime
