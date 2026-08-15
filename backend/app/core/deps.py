from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.denylist import is_denied
from app.core.permissions import role_has_permission, set_permission_overrides
from app.core.security import decode_token
from app.core.tenant import apply_tenant, tenant_id
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User
from app.services.activity import audit

DbDep = Annotated[Session, Depends(get_db)]


def _extract_token(
    authorization: str | None,
    access_cookie: str | None,
) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return access_cookie


def get_current_user(
    db: DbDep,
    authorization: Annotated[str | None, Header()] = None,
    ss_access: Annotated[str | None, Cookie()] = None,
) -> User:
    token = _extract_token(authorization, ss_access)
    if not token:
        # #region agent log
        try:
            import json, time
            from pathlib import Path

            Path(__file__).resolve().parents[3].joinpath("debug-1d8612.log").open("a", encoding="utf-8").write(
                json.dumps(
                    {
                        "sessionId": "1d8612",
                        "runId": "pre-fix",
                        "hypothesisId": "A",
                        "location": "deps.py:get_current_user",
                        "message": "missing access token",
                        "data": {"hasBearer": bool(authorization), "hasAccessCookie": bool(ss_access)},
                        "timestamp": int(time.time() * 1000),
                    }
                )
                + "\n"
            )
        except Exception:
            pass
        # #endregion
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        # #region agent log
        try:
            import json, time
            from pathlib import Path

            Path(__file__).resolve().parents[3].joinpath("debug-1d8612.log").open("a", encoding="utf-8").write(
                json.dumps(
                    {
                        "sessionId": "1d8612",
                        "runId": "pre-fix",
                        "hypothesisId": "A",
                        "location": "deps.py:get_current_user",
                        "message": "invalid or expired access token",
                        "data": {"hasPayload": bool(payload), "tokenType": (payload or {}).get("type")},
                        "timestamp": int(time.time() * 1000),
                    }
                )
                + "\n"
            )
        except Exception:
            pass
        # #endregion
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if is_denied(payload.get("jti")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session revoked")

    user_id = payload.get("sub")
    user = db.get(User, UUID(user_id)) if user_id else None
    if not user or not user.is_active or user.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account unavailable")
    apply_tenant(db, tenant_id(user))
    org = db.get(Organization, tenant_id(user))
    set_permission_overrides(getattr(org, "permission_overrides", None) if org else None)
    from app.core.observability import tag_request_role

    tag_request_role(user.role_key)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permission(permission: str):
    def checker(user: CurrentUser, db: DbDep, request: Request) -> User:
        if not role_has_permission(user.role_key, permission):
            audit(
                db,
                user=user,
                action="authz.denied",
                entity_type="permission",
                request=request,
                meta={"permission": permission},
            )
            db.commit()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return checker
