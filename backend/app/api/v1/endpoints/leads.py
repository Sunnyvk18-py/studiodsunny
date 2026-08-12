from fastapi import APIRouter
from sqlalchemy import select

from app.core.authz import require_founder_or_pm
from app.core.deps import CurrentUser, DbDep
from app.models.lead import Lead
from app.schemas.misc import LeadOut

router = APIRouter()


@router.get("", response_model=list[LeadOut])
def list_leads(db: DbDep, user: CurrentUser):
    require_founder_or_pm(user)
    leads = db.scalars(select(Lead).where(Lead.deleted_at.is_(None)).order_by(Lead.created_at.desc())).all()
    return [LeadOut.model_validate(l) for l in leads]
