from uuid import UUID, uuid4

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.tenant import STUDIO_SUNNY_ORG_ID
from app.db.base import Base, TimestampMixin
from app.db.types import GUID


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    legal_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    billing_entity: Mapped[str | None] = mapped_column(String(200), nullable=True)
    public_site: Mapped[str | None] = mapped_column(String(200), nullable=True)
    hq_domain: Mapped[str | None] = mapped_column(String(200), nullable=True)
    client_portal_domain: Mapped[str | None] = mapped_column(String(200), nullable=True)
    careers_domain: Mapped[str | None] = mapped_column(String(200), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata", nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)
    # Additive permission extras per role_key, e.g. {"developer": ["leads:read"]}
    permission_overrides: Mapped[dict | None] = mapped_column(JSON, nullable=True)


def default_org() -> Organization:
    return Organization(
        id=STUDIO_SUNNY_ORG_ID,
        name="Studio Sunny",
        slug="studio-sunny",
        legal_name="Studio Sunny Private Limited",
        billing_entity="Studio Sunny",
        public_site="https://studiosunny.com",
        hq_domain="hq.studiosunny.com",
        client_portal_domain="client.studiosunny.com",
        careers_domain="careers.studiosunny.com",
        timezone="Asia/Kolkata",
        currency="INR",
        permission_overrides={},
    )
