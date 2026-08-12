from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import or_, select

from app.core.config import settings
from app.core.deps import CurrentUser, DbDep
from app.core.permissions import Perm, role_has_permission
from app.core.security import decode_token
from app.core.tenant import tenant_id
from app.db.base import utcnow
from app.db.session import SessionLocal
from app.models.client import Client
from app.models.document import EMPTY_DOC, Document
from app.models.project import Project
from app.models.user import User
from app.realtime.docs import b64decode, b64encode, doc_collab
from app.realtime.hub import hub
from app.schemas.document import DocumentCreate, DocumentListItem, DocumentOut, DocumentUpdate, YjsStateOut
from app.services.activity import audit, log_activity
from app.utils import unique_slug

router = APIRouter()


def _require_read(user: User) -> None:
    if not role_has_permission(user.role_key, Perm.FILES_READ):
        raise HTTPException(403, "Cannot read documents")


def _require_write(user: User) -> None:
    if not role_has_permission(user.role_key, Perm.FILES_WRITE):
        raise HTTPException(403, "Cannot write documents")


def _can_read_doc(db, user: User, doc: Document) -> bool:
    from app.core.authz import is_founder_or_pm, is_project_member

    if is_founder_or_pm(user):
        return True
    if doc.created_by_id == user.id:
        return True
    if doc.project_id and is_project_member(db, user, doc.project_id):
        return True
    return False


def _can_write_doc(db, user: User, doc: Document) -> bool:
    from app.core.authz import is_founder

    # PERMISSIONS.md: founder or author/editor
    if is_founder(user):
        return True
    return doc.created_by_id == user.id


def _plain_from_content(content: dict | None) -> str:
    if not content:
        return ""
    chunks: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "text" and node.get("text"):
                chunks.append(str(node["text"]))
            for child in node.get("content") or []:
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(content)
    return " ".join(chunks).strip()[:8000]


def _hydrate(db, doc: Document) -> DocumentOut:
    project = db.get(Project, doc.project_id) if doc.project_id else None
    client = db.get(Client, doc.client_id) if doc.client_id else None
    author = db.get(User, doc.updated_by_id or doc.created_by_id)
    data = DocumentOut.model_validate(doc)
    data.project_name = project.name if project else None
    data.client_name = client.business_name if client else None
    data.author_name = author.display_name if author else None
    data.has_yjs_state = bool(doc.yjs_state)
    return data


def _list_item(db, doc: Document) -> DocumentListItem:
    full = _hydrate(db, doc)
    return DocumentListItem.model_validate(full.model_dump(exclude={"content", "plain_text"}))


@router.get("", response_model=list[DocumentListItem])
def list_docs(
    db: DbDep,
    user: CurrentUser,
    q: str | None = None,
    project_id: UUID | None = None,
    client_id: UUID | None = None,
    kind: str | None = None,
    limit: int = Query(80, ge=1, le=200),
):
    _require_read(user)
    stmt = select(Document).where(Document.deleted_at.is_(None)).order_by(Document.updated_at.desc())
    if project_id:
        stmt = stmt.where(Document.project_id == project_id)
    if client_id:
        stmt = stmt.where(Document.client_id == client_id)
    if kind:
        stmt = stmt.where(Document.kind == kind)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Document.title.ilike(like),
                Document.summary.ilike(like),
                Document.plain_text.ilike(like),
            )
        )
    rows = [d for d in db.scalars(stmt.limit(limit)).all() if _can_read_doc(db, user, d)]
    return [_list_item(db, d) for d in rows]


@router.get("/{doc_id}", response_model=DocumentOut)
def get_doc(doc_id: UUID, db: DbDep, user: CurrentUser):
    from app.core.authz import not_found

    _require_read(user)
    doc = db.get(Document, doc_id)
    if not doc or doc.deleted_at or not _can_read_doc(db, user, doc):
        raise not_found("Document")
    return _hydrate(db, doc)


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def create_doc(payload: DocumentCreate, db: DbDep, user: CurrentUser):
    _require_write(user)
    content = payload.content or EMPTY_DOC
    doc = Document(
        title=payload.title.strip(),
        slug=unique_slug(db, Document, payload.title),
        kind=payload.kind or "page",
        status=payload.status or "draft",
        summary=payload.summary,
        content=content,
        plain_text=_plain_from_content(content),
        project_id=payload.project_id,
        client_id=payload.client_id,
        created_by_id=user.id,
        updated_by_id=user.id,
        org_id=tenant_id(user),
    )
    db.add(doc)
    db.flush()
    log_activity(
        db,
        actor=user,
        verb="created",
        entity_type="document",
        entity_id=doc.id,
        project_id=doc.project_id,
        client_id=doc.client_id,
        summary=f"{user.display_name} created doc “{doc.title}”",
    )
    audit(db, user=user, action="document.create", entity_type="document", entity_id=doc.id)
    db.commit()
    db.refresh(doc)
    return _hydrate(db, doc)


@router.patch("/{doc_id}", response_model=DocumentOut)
def update_doc(doc_id: UUID, payload: DocumentUpdate, db: DbDep, user: CurrentUser):
    from app.core.authz import not_found

    _require_write(user)
    doc = db.get(Document, doc_id)
    if not doc or doc.deleted_at or not _can_write_doc(db, user, doc):
        raise not_found("Document")
    data = payload.model_dump(exclude_unset=True)
    yjs_b64 = data.pop("yjs_state_b64", None)
    if "title" in data and data["title"]:
        data["title"] = data["title"].strip()
    if "content" in data:
        data["plain_text"] = _plain_from_content(data["content"])
    for k, v in data.items():
        setattr(doc, k, v)
    if yjs_b64 is not None:
        doc.yjs_state = b64decode(yjs_b64) if yjs_b64 else None
    doc.updated_by_id = user.id
    doc.updated_at = utcnow()
    db.add(doc)
    audit(
        db,
        user=user,
        action="document.update",
        entity_type="document",
        entity_id=doc.id,
        meta={"title": doc.title},
    )
    db.commit()
    db.refresh(doc)
    return _hydrate(db, doc)


@router.get("/{doc_id}/yjs", response_model=YjsStateOut)
def get_yjs_state(doc_id: UUID, db: DbDep, user: CurrentUser):
    from app.core.authz import not_found

    _require_read(user)
    doc = db.get(Document, doc_id)
    if not doc or doc.deleted_at or not _can_read_doc(db, user, doc):
        raise not_found("Document")
    return YjsStateOut(yjs_state_b64=b64encode(doc.yjs_state) if doc.yjs_state else None)


@router.websocket("/{doc_id}/collab")
async def doc_collab_ws(websocket: WebSocket, doc_id: UUID):
    token = websocket.cookies.get(settings.access_cookie_name)
    payload = decode_token(token or "")
    if not payload or payload.get("type") != "access":
        await websocket.close(code=4401)
        return
    db = SessionLocal()
    try:
        user = db.get(User, UUID(str(payload.get("sub"))))
        doc = db.get(Document, doc_id)
        if not user or not user.is_active or not doc or doc.deleted_at:
            await websocket.close(code=4403)
            return
        # Collab = write surface (PERMISSIONS.md)
        if not _can_write_doc(db, user, doc):
            await websocket.close(code=4403)
            return
        await hub.connect(
            websocket,
            {
                "id": str(user.id),
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
            },
        )
        await doc_collab.subscribe(websocket, str(doc_id))
        # Seed current CRDT state to this client
        if doc.yjs_state:
            await websocket.send_json(
                {
                    "type": "yjs-init",
                    "doc_id": str(doc_id),
                    "update": b64encode(doc.yjs_state),
                    "sender_id": "server",
                }
            )
        await websocket.send_json(
            {
                "type": "presence",
                "doc_id": str(doc_id),
                "user": {"id": str(user.id), "display_name": user.display_name},
            }
        )
        while True:
            message = await websocket.receive_json()
            mtype = message.get("type")
            if mtype == "yjs":
                update = message.get("update")
                if update:
                    await doc_collab.publish_update(str(doc_id), update, str(user.id))
            elif mtype == "awareness":
                await doc_collab.publish_awareness(
                    str(doc_id),
                    message.get("awareness") or {},
                    str(user.id),
                )
            elif mtype == "awareness-bin":
                update = message.get("update")
                if update:
                    await doc_collab.publish_awareness_bin(
                        str(doc_id),
                        update,
                        message.get("sender_id") or str(user.id),
                        message.get("awareness") or {},
                    )
            elif mtype == "persist":
                update = message.get("update")
                content = message.get("content")
                if update or content is not None:
                    # Re-check write permission on every persist (membership/author can change).
                    fresh_user = db.get(User, UUID(str(payload.get("sub"))))
                    fresh = db.get(Document, doc_id)
                    if (
                        not fresh_user
                        or not fresh
                        or fresh.deleted_at
                        or not _can_write_doc(db, fresh_user, fresh)
                    ):
                        await websocket.close(code=4403)
                        return
                    if update:
                        fresh.yjs_state = b64decode(update)
                    if content is not None:
                        fresh.content = content
                        fresh.plain_text = _plain_from_content(content)
                    fresh.updated_by_id = fresh_user.id
                    fresh.updated_at = utcnow()
                    db.add(fresh)
                    db.commit()
            elif mtype == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(websocket)
        db.close()


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_doc(doc_id: UUID, db: DbDep, user: CurrentUser):
    from app.core.authz import not_found

    _require_write(user)
    doc = db.get(Document, doc_id)
    if not doc or doc.deleted_at or not _can_write_doc(db, user, doc):
        raise not_found("Document")
    doc.deleted_at = utcnow()
    doc.updated_by_id = user.id
    db.add(doc)
    audit(db, user=user, action="document.delete", entity_type="document", entity_id=doc.id)
    db.commit()
    return None
