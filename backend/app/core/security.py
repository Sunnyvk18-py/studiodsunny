from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Argon2id (OWASP: 19 MiB, t=2, p=1). bcrypt kept so existing hashes still verify.
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    argon2__memory_cost=19456,
    argon2__time_cost=2,
    argon2__parallelism=1,
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def needs_rehash(hashed: str) -> bool:
    return pwd_context.needs_update(hashed)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(
    subject: str | UUID,
    extra: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    expire = _utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": _utcnow(),
        "type": "access",
        "jti": str(uuid4()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: str | UUID, token_id: str, family_id: str) -> str:
    expire = _utcnow() + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": str(subject),
        "exp": expire,
        "iat": _utcnow(),
        "type": "refresh",
        "jti": token_id,
        "fid": family_id,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None


def remaining_ttl_seconds(payload: dict[str, Any]) -> int:
    exp = payload.get("exp")
    if not exp:
        return 0
    try:
        exp_dt = datetime.fromtimestamp(int(exp), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return 0
    return max(0, int((exp_dt - _utcnow()).total_seconds()))
