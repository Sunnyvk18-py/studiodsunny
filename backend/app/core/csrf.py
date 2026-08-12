import hmac
import secrets

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
EXEMPT_SUFFIXES = (
    "/auth/login",
    "/auth/logout",
    "/auth/2fa/verify",
    "/auth/google/start",
    "/auth/google/callback",
    "/auth/forgot-password",
    "/auth/reset-password",
    "/auth/accept-invite",
    "/health",
)


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response: Response, token: str) -> None:
    kwargs = {
        "httponly": False,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "path": "/",
        "max_age": settings.refresh_token_expire_days * 24 * 3600,
    }
    if settings.cookie_domain:
        kwargs["domain"] = settings.cookie_domain
    response.set_cookie(settings.csrf_cookie_name, token, **kwargs)


def clear_csrf_cookie(response: Response) -> None:
    kwargs = {"path": "/"}
    if settings.cookie_domain:
        kwargs["domain"] = settings.cookie_domain
    response.delete_cookie(settings.csrf_cookie_name, **kwargs)


def _exempt(path: str) -> bool:
    if not path.startswith(settings.api_v1_prefix) and path != "/health":
        return True
    return any(path.endswith(s) or path == s for s in EXEMPT_SUFFIXES)


class CsrfMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method not in SAFE_METHODS and not _exempt(request.url.path):
            cookie = request.cookies.get(settings.csrf_cookie_name)
            header = request.headers.get("x-csrf-token")
            if not cookie or not header or not hmac.compare_digest(cookie, header):
                return JSONResponse({"detail": "CSRF check failed"}, status_code=403)
        return await call_next(request)
