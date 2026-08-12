from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.authz import not_found
from app.core.config import settings
from app.core.deps import CurrentUser, DbDep
from app.core.pagination import LimitQuery, clamp_limit
from app.core.permissions import Perm, role_has_permission
from app.core.security import decode_token
from app.core.tenant import tenant_id
from app.db.session import SessionLocal
from app.models.chat import ChatChannel, ChatChannelMember, ChatMessage
from app.models.user import User
from app.realtime.hub import hub
from app.schemas.common import ORMModel, UserBrief
from app.services.activity import audit

router = APIRouter()


class ChannelOut(ORMModel):
    id: UUID
    slug: str
    name: str
    kind: str
    topic: str | None = None


class MessageOut(ORMModel):
    id: UUID
    channel_id: UUID
    author_id: UUID
    body: str
    created_at: datetime
    author: UserBrief | None = None


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=8000)


class MessageUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=8000)


def _require(user: User, perm: str) -> None:
    if not role_has_permission(user.role_key, perm):
        raise HTTPException(403, "Insufficient permissions")


def _is_channel_member(db, user: User, channel_id: UUID) -> bool:
    return (
        db.scalar(
            select(ChatChannelMember.id).where(
                ChatChannelMember.channel_id == channel_id,
                ChatChannelMember.user_id == user.id,
            )
        )
        is not None
    )


def _serialize_message(msg: ChatMessage, author: User | None) -> MessageOut:
    brief = None
    if author:
        brief = UserBrief(
            id=author.id,
            email=author.email,
            display_name=author.display_name,
            role_key=author.role_key,
            avatar_url=author.avatar_url,
        )
    return MessageOut(
        id=msg.id,
        channel_id=msg.channel_id,
        author_id=msg.author_id,
        body=msg.body,
        created_at=msg.created_at,
        author=brief,
    )


@router.get("/channels", response_model=list[ChannelOut])
def list_channels(db: DbDep, user: CurrentUser):
    _require(user, Perm.MESSAGES_READ)
    member_ids = db.scalars(
        select(ChatChannelMember.channel_id).where(ChatChannelMember.user_id == user.id)
    ).all()
    if not member_ids:
        return []
    rows = db.scalars(
        select(ChatChannel).where(ChatChannel.id.in_(member_ids)).order_by(ChatChannel.name)
    ).all()
    return rows


@router.get("/channels/{slug}/messages", response_model=list[MessageOut])
def list_messages(
    slug: str,
    db: DbDep,
    user: CurrentUser,
    limit: int = LimitQuery(50),
    before: datetime | None = Query(None, description="Cursor: created_at strictly before"),
):
    _require(user, Perm.MESSAGES_READ)
    limit = clamp_limit(limit)
    channel = db.scalar(select(ChatChannel).where(ChatChannel.slug == slug))
    if not channel or not _is_channel_member(db, user, channel.id):
        raise not_found("Channel")
    q = select(ChatMessage).where(ChatMessage.channel_id == channel.id)
    if before:
        q = q.where(ChatMessage.created_at < before)
    rows = db.scalars(q.order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc()).limit(limit)).all()
    authors = {
        u.id: u
        for u in db.scalars(select(User).where(User.id.in_({m.author_id for m in rows} or {user.id}))).all()
    }
    return [_serialize_message(m, authors.get(m.author_id)) for m in reversed(rows)]


@router.post("/channels/{slug}/messages", response_model=MessageOut, status_code=201)
async def post_message(slug: str, payload: MessageCreate, db: DbDep, user: CurrentUser):
    _require(user, Perm.MESSAGES_WRITE)
    channel = db.scalar(select(ChatChannel).where(ChatChannel.slug == slug))
    if not channel or not _is_channel_member(db, user, channel.id):
        raise not_found("Channel")
    msg = ChatMessage(
        channel_id=channel.id,
        author_id=user.id,
        body=payload.body.strip(),
        org_id=tenant_id(user),
    )
    db.add(msg)
    audit(db, user=user, action="chat.message", entity_type="chat", entity_id=channel.id, meta={"slug": slug})
    db.commit()
    db.refresh(msg)
    out = _serialize_message(msg, user)
    await hub.publish(
        slug,
        {"type": "message", "channel": slug, "message": out.model_dump(mode="json")},
    )
    return out


@router.patch("/channels/{slug}/messages/{message_id}", response_model=MessageOut)
async def update_message(slug: str, message_id: UUID, payload: MessageUpdate, db: DbDep, user: CurrentUser):
    from app.core.authz import is_founder

    _require(user, Perm.MESSAGES_WRITE)
    channel = db.scalar(select(ChatChannel).where(ChatChannel.slug == slug))
    if not channel or not _is_channel_member(db, user, channel.id):
        raise not_found("Channel")
    msg = db.get(ChatMessage, message_id)
    if not msg or msg.channel_id != channel.id:
        raise not_found("Message")
    if not is_founder(user) and msg.author_id != user.id:
        raise not_found("Message")
    msg.body = payload.body.strip()
    db.add(msg)
    audit(db, user=user, action="chat.message_update", entity_type="chat", entity_id=msg.id, meta={"slug": slug})
    db.commit()
    db.refresh(msg)
    out = _serialize_message(msg, user if msg.author_id == user.id else db.get(User, msg.author_id))
    await hub.publish(
        slug,
        {"type": "message_updated", "channel": slug, "message": out.model_dump(mode="json")},
    )
    return out


@router.delete("/channels/{slug}/messages/{message_id}", status_code=204)
async def delete_message(slug: str, message_id: UUID, db: DbDep, user: CurrentUser):
    from app.core.authz import is_founder

    _require(user, Perm.MESSAGES_WRITE)
    channel = db.scalar(select(ChatChannel).where(ChatChannel.slug == slug))
    if not channel or not _is_channel_member(db, user, channel.id):
        raise not_found("Channel")
    msg = db.get(ChatMessage, message_id)
    if not msg or msg.channel_id != channel.id:
        raise not_found("Message")
    if not is_founder(user) and msg.author_id != user.id:
        raise not_found("Message")
    db.delete(msg)
    audit(db, user=user, action="chat.message_delete", entity_type="chat", entity_id=message_id, meta={"slug": slug})
    db.commit()
    await hub.publish(
        slug,
        {"type": "message_deleted", "channel": slug, "message_id": str(message_id)},
    )
    return None


@router.websocket("/ws")
async def chat_ws(websocket: WebSocket):
    token = websocket.cookies.get(settings.access_cookie_name)
    payload = decode_token(token or "")
    if not payload or payload.get("type") != "access":
        await websocket.close(code=4401)
        return

    db = SessionLocal()
    try:
        user = db.get(User, UUID(str(payload.get("sub"))))
        if not user or not user.is_active or not role_has_permission(user.role_key, Perm.MESSAGES_READ):
            await websocket.close(code=4403)
            return
        user_brief = {
            "id": str(user.id),
            "display_name": user.display_name,
            "role_key": user.role_key,
        }
        can_write = role_has_permission(user.role_key, Perm.MESSAGES_WRITE)
        user_id = user.id
    finally:
        db.close()

    await hub.connect(websocket, user_brief)
    try:
        while True:
            data = await websocket.receive_json()
            kind = data.get("type")
            channel = (data.get("channel") or "").strip()
            if kind == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            if not channel:
                continue
            if kind == "subscribe":
                db = SessionLocal()
                try:
                    row = db.scalar(select(ChatChannel).where(ChatChannel.slug == channel))
                    member = (
                        row
                        and db.scalar(
                            select(ChatChannelMember.id).where(
                                ChatChannelMember.channel_id == row.id,
                                ChatChannelMember.user_id == user_id,
                            )
                        )
                    )
                    if not member:
                        await websocket.send_json({"type": "error", "code": 4403, "channel": channel})
                        continue
                finally:
                    db.close()
                await hub.subscribe(websocket, channel)
                present = await hub.presence(channel)
                await websocket.send_json({"type": "presence", "channel": channel, "user_ids": present})
                continue
            if kind == "typing" and can_write:
                db = SessionLocal()
                try:
                    row = db.scalar(select(ChatChannel).where(ChatChannel.slug == channel))
                    member = (
                        row
                        and db.scalar(
                            select(ChatChannelMember.id).where(
                                ChatChannelMember.channel_id == row.id,
                                ChatChannelMember.user_id == user_id,
                            )
                        )
                    )
                    if not member:
                        continue
                finally:
                    db.close()
                await hub.publish(
                    channel,
                    {"type": "typing", "channel": channel, "user": user_brief},
                )
                continue
            if kind == "heartbeat":
                await hub.heartbeat(channel, user_brief["id"])
                present = await hub.presence(channel)
                await hub.publish(channel, {"type": "presence", "channel": channel, "user_ids": present})
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(websocket)
