from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.tenant import STUDIO_SUNNY_ORG_ID
from app.db.types import GUID


class TenantMixin:
    org_id: Mapped[UUID] = mapped_column(
        GUID,
        ForeignKey("organizations.id"),
        index=True,
        nullable=False,
        default=STUDIO_SUNNY_ORG_ID,
    )
