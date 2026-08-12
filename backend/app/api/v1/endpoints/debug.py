from fastapi import APIRouter

from app.core.authz import require_founder
from app.core.deps import CurrentUser

router = APIRouter()


@router.get("/boom")
def deliberate_boom(user: CurrentUser):
    """Founder-only probe — raises so Sentry can be verified end-to-end."""
    require_founder(user)
    raise RuntimeError("Sentry boom test — intentional")
