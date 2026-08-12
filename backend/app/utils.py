from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def unique_slug(db: Session, model, base: str) -> str:
    from app.services.project import slugify

    slug = slugify(base)
    candidate = slug
    i = 2
    while db.scalar(select(model.id).where(model.slug == candidate)):
        candidate = f"{slug}-{i}"
        i += 1
    return candidate


def user_brief_map(db: Session, user_ids: list) -> dict:
    if not user_ids:
        return {}
    users = db.scalars(select(User).where(User.id.in_(user_ids))).all()
    return {u.id: u for u in users}


def initials(name: str) -> str:
    parts = [p for p in name.split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()
