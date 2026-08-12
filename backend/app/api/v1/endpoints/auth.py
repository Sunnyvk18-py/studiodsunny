from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
import hmac
import secrets

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select, update

from app.core.config import settings
from app.core.client_ip import client_ip
from app.core.csrf import clear_csrf_cookie, new_csrf_token, set_csrf_cookie
from app.core.denylist import deny_jti, is_denied
from app.core.deps import CurrentUser, DbDep
from app.core.rate_limit import (
    LOGIN_EMAIL_LIMIT,
    LOGIN_EMAIL_WINDOW_SECONDS,
    LOGIN_IP_LIMIT,
    LOGIN_IP_WINDOW_SECONDS,
    TOTP_VERIFY_LIMIT,
    TOTP_VERIFY_WINDOW_SECONDS,
    login_email_limiter,
    login_ip_limiter,
    totp_verify_limiter,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    needs_rehash,
    remaining_ttl_seconds,
    verify_password,
)
from app.core.totp import new_totp_secret, totp_uri, verify_totp
from app.db.base import utcnow
from app.core.tenant import STUDIO_SUNNY_ORG_ID, apply_tenant, tenant_id
from app.models.session import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    AuthProvidersResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MeResponse,
    ResetPasswordRequest,
    AcceptInviteRequest,
    SessionOut,
    TokenUser,
    TotpCodeRequest,
    TotpDisableRequest,
    TotpSetupResponse,
    TotpVerifyRequest,
)
from app.models.auth_token import AuthToken
from app.models.organization import Organization
from app.core.permissions import set_permission_overrides, permissions_for_role
from app.services.email import send_email
from app.services.activity import audit
from app.utils import hash_token


router = APIRouter()

# Precomputed so missing-user login still pays verify cost (constant-ish timing).
_DUMMY_PASSWORD_HASH = hash_password("__sunny_hq_dummy_password_not_a_user__")


def _cookie_base() -> dict:
    kwargs = {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
    }
    if settings.cookie_domain:
        kwargs["domain"] = settings.cookie_domain
    return kwargs


def _access_cookie_kwargs() -> dict:
    return {**_cookie_base(), "path": "/"}


def _refresh_cookie_kwargs() -> dict:
    return {**_cookie_base(), "path": f"{settings.api_v1_prefix}/auth"}


def _oauth_state_cookie_kwargs() -> dict:
    return {**_cookie_base(), "path": f"{settings.api_v1_prefix}/auth/google", "max_age": 600}


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _client_ip(request: Request) -> str:
    return client_ip(request)


def _revoke_family(db, family_id: UUID | None) -> None:
    if not family_id:
        return
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


def _revoke_all_sessions(db, user_id: UUID) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


def _revoke_other_sessions(db, user_id: UUID, keep_id: UUID | None) -> None:
    stmt = update(RefreshToken).where(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at.is_(None),
    )
    if keep_id is not None:
        stmt = stmt.where(RefreshToken.id != keep_id)
    db.execute(stmt.values(revoked_at=utcnow()))


def _current_refresh_row(db, request: Request) -> RefreshToken | None:
    token = request.cookies.get(settings.refresh_cookie_name)
    if not token:
        return None
    return db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(token)))


def _set_auth_cookies(
    response: Response,
    user: User,
    db,
    request: Request | None = None,
    family_id: UUID | None = None,
) -> tuple[RefreshToken, str]:
    token_id = uuid4()
    family = family_id or uuid4()
    access = create_access_token(user.id, extra={"role": user.role_key})
    refresh = create_refresh_token(user.id, str(token_id), str(family))
    row = RefreshToken(
        id=token_id,
        user_id=user.id,
        family_id=family,
        token_hash=hash_token(refresh),
        expires_at=utcnow() + timedelta(days=settings.refresh_token_expire_days),
        user_agent=(request.headers.get("user-agent")[:300] if request else None),
        ip_address=_client_ip(request) if request else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    response.set_cookie(
        settings.access_cookie_name,
        access,
        max_age=settings.access_token_expire_minutes * 60,
        **_access_cookie_kwargs(),
    )
    response.set_cookie(
        settings.refresh_cookie_name,
        refresh,
        max_age=settings.refresh_token_expire_days * 24 * 3600,
        **_refresh_cookie_kwargs(),
    )
    csrf = new_csrf_token()
    set_csrf_cookie(response, csrf)
    return row, csrf


def serialize_me(user: User, db=None) -> TokenUser:
    if db is not None:
        org = db.get(Organization, tenant_id(user))
        set_permission_overrides(getattr(org, "permission_overrides", None) if org else None)
    emp_id = str(user.employee.id) if user.employee else None
    return TokenUser(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        first_name=user.first_name,
        last_name=user.last_name,
        role_key=user.role_key,
        avatar_url=user.avatar_url,
        is_superadmin=user.is_superadmin,
        permissions=permissions_for_role(user.role_key),
        employee_id=emp_id,
        org_id=str(tenant_id(user)),
        totp_enabled=bool(user.totp_enabled),
    )


def _deny_access_cookie(request: Request) -> None:
    token = request.cookies.get(settings.access_cookie_name)
    if not token:
        return
    payload = decode_token(token)
    if payload and payload.get("jti"):
        deny_jti(str(payload["jti"]), remaining_ttl_seconds(payload) or 1)


def _clear_oauth_state_cookie(response: Response) -> None:
    kwargs = {"path": f"{settings.api_v1_prefix}/auth/google"}
    if settings.cookie_domain:
        kwargs["domain"] = settings.cookie_domain
    response.delete_cookie(settings.oauth_state_cookie_name, **kwargs)


def _login_already_limited(request: Request, email: str) -> bool:
    ip = _client_ip(request)
    return login_ip_limiter.over_limit(
        f"login:ip:{ip}", limit=LOGIN_IP_LIMIT, window_seconds=LOGIN_IP_WINDOW_SECONDS
    ) or login_email_limiter.over_limit(
        f"login:email:{email}", limit=LOGIN_EMAIL_LIMIT, window_seconds=LOGIN_EMAIL_WINDOW_SECONDS
    )


def _record_login_failure(request: Request, email: str) -> bool:
    """Record a failed attempt. Returns True if this failure tripped the limit → 429."""
    ip = _client_ip(request)
    ip_ok = login_ip_limiter.hit(
        f"login:ip:{ip}", limit=LOGIN_IP_LIMIT, window_seconds=LOGIN_IP_WINDOW_SECONDS
    )
    email_ok = login_email_limiter.hit(
        f"login:email:{email}", limit=LOGIN_EMAIL_LIMIT, window_seconds=LOGIN_EMAIL_WINDOW_SECONDS
    )
    return not (ip_ok and email_ok)


@router.post("/login", response_model=MeResponse)
def login(payload: LoginRequest, response: Response, db: DbDep, request: Request):
    email = payload.email.lower()
    if _login_already_limited(request, email):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts")

    user = db.scalar(select(User).where(User.email == email, User.deleted_at.is_(None)))
    password_ok = verify_password(
        payload.password,
        user.hashed_password if user else _DUMMY_PASSWORD_HASH,
    )
    if not user or not password_ok:
        if _record_login_failure(request, email):
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts")
        audit(
            db,
            user=None,
            action="auth.login_failed",
            entity_type="auth",
            request=request,
            meta={"email": email},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    if needs_rehash(user.hashed_password):
        user.hashed_password = hash_password(payload.password)
        db.add(user)

    apply_tenant(db, tenant_id(user))
    if user.totp_enabled and user.totp_secret:
        temp = create_access_token(
            user.id,
            extra={"type": "pending_2fa"},
            expires_delta=timedelta(minutes=5),
        )
        audit(db, user=user, action="auth.login_2fa_required", entity_type="auth", request=request)
        db.commit()
        return MeResponse(needs_2fa=True, temp_token=temp)

    user.last_login_at = utcnow()
    db.add(user)
    audit(db, user=user, action="auth.login", entity_type="auth", request=request)
    _, csrf = _set_auth_cookies(response, user, db, request)
    return MeResponse(user=serialize_me(user, db), csrf_token=csrf)


@router.post("/refresh", response_model=MeResponse)
def refresh_session(response: Response, db: DbDep, request: Request):
    token = request.cookies.get(settings.refresh_cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="Missing refresh token")
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(token)))
    if not stored or _aware(stored.expires_at) < utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired")

    if stored.revoked_at:
        _revoke_family(db, stored.family_id)
        audit(
            db,
            user=None,
            action="auth.refresh_reuse",
            entity_type="auth",
            request=request,
            meta={"family_id": str(stored.family_id) if stored.family_id else None},
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token reuse detected. Sign in again.")

    user = db.get(User, stored.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Account unavailable")

    stored.revoked_at = utcnow()
    db.add(stored)
    db.flush()
    new_row, csrf = _set_auth_cookies(response, user, db, request, family_id=stored.family_id or uuid4())
    stored.replaced_by_id = new_row.id
    db.add(stored)
    db.commit()
    return MeResponse(user=serialize_me(user, db), csrf_token=csrf)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, db: DbDep, request: Request):
    token = request.cookies.get(settings.refresh_cookie_name)
    if token:
        stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(token)))
        if stored and not stored.revoked_at:
            stored.revoked_at = utcnow()
            db.add(stored)
            audit(
                db,
                user=None,
                action="auth.logout",
                entity_type="auth",
                request=request,
                meta={"user_id": str(stored.user_id)},
            )
            db.commit()
    _deny_access_cookie(request)
    response.delete_cookie(settings.access_cookie_name, **_access_cookie_kwargs())
    response.delete_cookie(settings.refresh_cookie_name, **_refresh_cookie_kwargs())
    clear_csrf_cookie(response)
    return None


@router.post("/logout-all")
def logout_all(response: Response, db: DbDep, request: Request, user: CurrentUser):
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    audit(db, user=user, action="auth.logout_all", entity_type="auth", request=request)
    db.commit()
    _deny_access_cookie(request)
    response.delete_cookie(settings.access_cookie_name, **_access_cookie_kwargs())
    response.delete_cookie(settings.refresh_cookie_name, **_refresh_cookie_kwargs())
    clear_csrf_cookie(response)
    return {"message": "Signed out everywhere"}


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUser, request: Request, response: Response, db: DbDep):
    token = request.cookies.get(settings.csrf_cookie_name) or new_csrf_token()
    if not request.cookies.get(settings.csrf_cookie_name):
        set_csrf_cookie(response, token)
    return MeResponse(user=serialize_me(user, db), csrf_token=token)


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(db: DbDep, request: Request, user: CurrentUser):
    current = _current_refresh_row(db, request)
    current_id = current.id if current and not current.revoked_at else None
    rows = db.scalars(
        select(RefreshToken)
        .where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > utcnow(),
        )
        .order_by(RefreshToken.created_at.desc())
    ).all()
    out: list[SessionOut] = []
    for row in rows:
        created = _aware(getattr(row, "created_at", None))
        out.append(
            SessionOut(
                id=str(row.id),
                created_at=created.isoformat() if created else None,
                user_agent=row.user_agent,
                ip=row.ip_address,
                current=bool(current_id and row.id == current_id),
            )
        )
    return out


@router.delete("/sessions/{id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_session(id: UUID, db: DbDep, request: Request, user: CurrentUser):
    row = db.get(RefreshToken, id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if not row.revoked_at:
        _revoke_family(db, row.family_id or row.id)
        audit(
            db,
            user=user,
            action="auth.session_revoke",
            entity_type="auth",
            request=request,
            meta={"session_id": str(id)},
        )
        db.commit()
    return None


@router.get("/providers", response_model=AuthProvidersResponse)
def auth_providers():
    return AuthProvidersResponse(google=settings.google_oauth_enabled)


@router.post("/2fa/verify", response_model=MeResponse)
def verify_2fa(payload: TotpVerifyRequest, response: Response, db: DbDep, request: Request):
    token_payload = decode_token(payload.temp_token)
    if not token_payload or token_payload.get("type") != "pending_2fa":
        raise HTTPException(401, "Invalid or expired 2FA session")
    jti = str(token_payload.get("jti") or "")
    if not jti or is_denied(jti):
        raise HTTPException(401, "Invalid or expired 2FA session")

    # Already burned after 5 failures — do not allow wait-and-retry on the same token.
    if totp_verify_limiter.over_limit(
        f"2fa:{jti}", limit=TOTP_VERIFY_LIMIT, window_seconds=TOTP_VERIFY_WINDOW_SECONDS
    ):
        deny_jti(jti, remaining_ttl_seconds(token_payload) or 1)
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many 2FA attempts")

    user = db.get(User, UUID(token_payload["sub"]))
    if not user or not user.totp_enabled or not user.totp_secret:
        raise HTTPException(401, "2FA is not enabled")
    if not verify_totp(user.totp_secret, payload.code):
        recorded = totp_verify_limiter.hit(
            f"2fa:{jti}", limit=TOTP_VERIFY_LIMIT, window_seconds=TOTP_VERIFY_WINDOW_SECONDS
        )
        audit(db, user=user, action="auth.2fa_failed", entity_type="auth", request=request)
        db.commit()
        # Fifth failure (or hit refused) destroys the pending token — force fresh password login.
        if (not recorded) or totp_verify_limiter.over_limit(
            f"2fa:{jti}", limit=TOTP_VERIFY_LIMIT, window_seconds=TOTP_VERIFY_WINDOW_SECONDS
        ):
            deny_jti(jti, remaining_ttl_seconds(token_payload) or 1)
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many 2FA attempts")
        raise HTTPException(401, "Invalid authenticator code")

    # Successful verify — burn the pending token so it cannot be reused.
    deny_jti(jti, remaining_ttl_seconds(token_payload) or 1)
    totp_verify_limiter.reset(f"2fa:{jti}")
    apply_tenant(db, tenant_id(user))
    user.last_login_at = utcnow()
    db.add(user)
    audit(db, user=user, action="auth.login", entity_type="auth", request=request, meta={"method": "2fa"})
    _, csrf = _set_auth_cookies(response, user, db, request)
    return MeResponse(user=serialize_me(user, db), csrf_token=csrf)


@router.post("/2fa/setup", response_model=TotpSetupResponse)
def setup_2fa(db: DbDep, user: CurrentUser):
    secret = user.totp_secret or new_totp_secret()
    user.totp_secret = secret
    db.add(user)
    db.commit()
    return TotpSetupResponse(secret=secret, otpauth_url=totp_uri(secret, user.email), enabled=user.totp_enabled)


@router.post("/2fa/enable", response_model=MeResponse)
def enable_2fa(payload: TotpCodeRequest, db: DbDep, user: CurrentUser, request: Request, response: Response):
    if not user.totp_secret:
        raise HTTPException(400, "Call /2fa/setup first")
    if not verify_totp(user.totp_secret, payload.code):
        raise HTTPException(400, "Invalid authenticator code")
    user.totp_enabled = True
    db.add(user)
    audit(db, user=user, action="auth.2fa_enabled", entity_type="auth", request=request)
    db.commit()
    token = request.cookies.get(settings.csrf_cookie_name) or new_csrf_token()
    return MeResponse(user=serialize_me(user, db), csrf_token=token)


@router.post("/2fa/disable", response_model=MeResponse)
def disable_2fa(payload: TotpDisableRequest, db: DbDep, user: CurrentUser, request: Request):
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")
    if user.totp_enabled and user.totp_secret and not verify_totp(user.totp_secret, payload.code):
        raise HTTPException(400, "Invalid authenticator code")
    user.totp_enabled = False
    user.totp_secret = None
    db.add(user)
    audit(db, user=user, action="auth.2fa_disabled", entity_type="auth", request=request)
    db.commit()
    return MeResponse(user=serialize_me(user, db))


@router.get("/google/start")
def google_start():
    if not settings.google_oauth_enabled:
        raise HTTPException(501, "Google SSO is not configured")
    from urllib.parse import urlencode

    state = secrets.token_urlsafe(32)
    params = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "online",
            "prompt": "select_account",
            "state": state,
        }
    )
    redirect = RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")
    redirect.set_cookie(settings.oauth_state_cookie_name, state, **_oauth_state_cookie_kwargs())
    return redirect


@router.get("/google/callback")
async def google_callback(
    code: str,
    response: Response,
    db: DbDep,
    request: Request,
    state: str | None = None,
):
    if not settings.google_oauth_enabled:
        raise HTTPException(501, "Google SSO is not configured")
    import httpx

    cookie_state = request.cookies.get(settings.oauth_state_cookie_name)
    if (
        not state
        or not cookie_state
        or not hmac.compare_digest(state, cookie_state)
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")

    async with httpx.AsyncClient(timeout=20) as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_res.status_code >= 400:
            raise HTTPException(400, "Google token exchange failed")
        access = token_res.json().get("access_token")
        info_res = await client.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {access}"},
        )
        if info_res.status_code >= 400:
            raise HTTPException(400, "Google userinfo failed")
        info = info_res.json()

    email = (info.get("email") or "").lower()
    sub = info.get("sub")
    if not email or not sub:
        raise HTTPException(400, "Google account missing email")
    domain = email.split("@")[-1]
    allowed = (settings.google_allowed_domain or "").lower().strip()
    if allowed and domain != allowed:
        raise HTTPException(403, "Google account domain not allowed")

    user = db.scalar(select(User).where(User.google_sub == sub)) or db.scalar(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    )
    if not user:
        first = info.get("given_name") or email.split("@")[0]
        last = info.get("family_name") or ""
        user = User(
            email=email,
            hashed_password=hash_password(uuid4().hex + uuid4().hex),
            first_name=first,
            last_name=last,
            display_name=info.get("name") or first,
            avatar_url=info.get("picture"),
            role_key="freelancer",
            google_sub=sub,
            email_verified=bool(info.get("email_verified", True)),
            org_id=STUDIO_SUNNY_ORG_ID,
        )
        db.add(user)
        db.flush()
    else:
        user.google_sub = sub
        if info.get("picture") and not user.avatar_url:
            user.avatar_url = info.get("picture")
        db.add(user)

    if user.totp_enabled and user.totp_secret:
        temp = create_access_token(user.id, extra={"type": "pending_2fa"}, expires_delta=timedelta(minutes=5))
        db.commit()
        redirect = RedirectResponse(f"{settings.frontend_url}/login?totp=1&temp={temp}")
        _clear_oauth_state_cookie(redirect)
        return redirect

    apply_tenant(db, tenant_id(user))
    user.last_login_at = utcnow()
    db.add(user)
    audit(db, user=user, action="auth.login", entity_type="auth", request=request, meta={"method": "google"})
    redirect = RedirectResponse(f"{settings.frontend_url}/home")
    _set_auth_cookies(redirect, user, db, request)
    _clear_oauth_state_cookie(redirect)
    return redirect


def _issue_token(db, user: User, kind: str, ttl: timedelta = timedelta(hours=72)) -> str:
    raw = secrets.token_urlsafe(32)
    row = AuthToken(
        user_id=user.id,
        token_hash=hash_token(raw),
        kind=kind,
        expires_at=utcnow() + ttl,
        meta={},
    )
    db.add(row)
    return raw


@router.post("/change-password")
def change_password(payload: ChangePasswordRequest, db: DbDep, user: CurrentUser, request: Request):
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(400, "Current password is incorrect")
    if len(payload.new_password) < 8:
        raise HTTPException(400, "New password must be at least 8 characters")
    user.hashed_password = hash_password(payload.new_password)
    db.add(user)
    current = _current_refresh_row(db, request)
    keep_id = current.id if current and current.user_id == user.id else None
    _revoke_other_sessions(db, user.id, keep_id)
    audit(db, user=user, action="auth.password_change", entity_type="auth", request=request)
    db.commit()
    return {"ok": True}


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
def forgot_password(payload: ForgotPasswordRequest, db: DbDep, request: Request):
    """Always 204 to avoid email enumeration."""
    user = db.scalar(select(User).where(User.email == payload.email.lower(), User.deleted_at.is_(None)))
    if user and user.is_active:
        raw = _issue_token(db, user, "password_reset", ttl=timedelta(minutes=30))
        reset_url = f"{settings.frontend_url}/reset-password?token={raw}"
        send_email(
            user.email,
            "Reset your Studio Sunny HQ password",
            f"Reset your password:\n\n{reset_url}\n\nThis link expires in 30 minutes.",
        )
        audit(db, user=user, action="auth.password_reset_requested", entity_type="auth", request=request)
        db.commit()
    return None


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: DbDep, request: Request):
    row = db.scalar(
        select(AuthToken).where(AuthToken.token_hash == hash_token(payload.token), AuthToken.kind == "password_reset")
    )
    if not row or row.used_at or _aware(row.expires_at) < utcnow():
        raise HTTPException(400, "Invalid or expired reset link")
    user = db.get(User, row.user_id)
    if not user or user.deleted_at:
        raise HTTPException(400, "Account unavailable")
    if len(payload.new_password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    user.hashed_password = hash_password(payload.new_password)
    row.used_at = utcnow()
    db.add(user)
    db.add(row)
    _revoke_all_sessions(db, user.id)
    audit(db, user=user, action="auth.password_reset", entity_type="auth", request=request)
    db.commit()
    return {"ok": True}


@router.get("/invite/{token}")
def peek_invite(token: str, db: DbDep):
    row = db.scalar(select(AuthToken).where(AuthToken.token_hash == hash_token(token), AuthToken.kind == "invite"))
    if not row or row.used_at or _aware(row.expires_at) < utcnow():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")
    user = db.get(User, row.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")
    return {
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role_key": user.role_key,
        "display_name": user.display_name,
    }


@router.post("/accept-invite", response_model=MeResponse)
def accept_invite(payload: AcceptInviteRequest, response: Response, db: DbDep, request: Request):
    row = db.scalar(select(AuthToken).where(AuthToken.token_hash == hash_token(payload.token), AuthToken.kind == "invite"))
    if not row or row.used_at or _aware(row.expires_at) < utcnow():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")
    user = db.get(User, row.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")
    if len(payload.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    user.hashed_password = hash_password(payload.password)
    if payload.first_name:
        user.first_name = payload.first_name
    if payload.last_name is not None:
        user.last_name = payload.last_name
    user.display_name = f"{user.first_name} {user.last_name}".strip()
    user.is_active = True
    user.email_verified = True
    row.used_at = utcnow()
    db.add(user)
    db.add(row)
    apply_tenant(db, tenant_id(user))
    audit(db, user=user, action="auth.invite_accepted", entity_type="auth", request=request)
    _, csrf = _set_auth_cookies(response, user, db, request)
    return MeResponse(user=serialize_me(user, db), csrf_token=csrf)
