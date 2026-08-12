from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import or_, select

from app.core.config import settings
from app.core.deps import CurrentUser, DbDep
from app.core.pagination import LimitQuery, apply_created_before_cursor, clamp_limit
from app.core.permissions import Perm, role_has_permission
from app.core.tenant import tenant_id
from app.db.base import utcnow
from app.models.client import Client
from app.models.file_asset import FileAsset
from app.models.project import Project
from app.models.user import User
from app.schemas.file import FileOut, FileUpdate
from app.services.activity import audit, log_activity
from app.services import storage as store

router = APIRouter()


def _require_read(user: User, kind: str | None = None) -> None:
    if kind == "credential" and not role_has_permission(user.role_key, Perm.CREDENTIALS_READ):
        raise HTTPException(403, "Credential vault is restricted")
    if not role_has_permission(user.role_key, Perm.FILES_READ):
        raise HTTPException(403, "Cannot read files")


def _require_write(user: User, kind: str | None = None) -> None:
    if kind == "credential" and not role_has_permission(user.role_key, Perm.CREDENTIALS_WRITE):
        raise HTTPException(403, "Cannot write credential vault")
    if not role_has_permission(user.role_key, Perm.FILES_WRITE):
        raise HTTPException(403, "Cannot write files")


def _hydrate(db, asset: FileAsset) -> FileOut:
    project = db.get(Project, asset.project_id) if asset.project_id else None
    client = db.get(Client, asset.client_id) if asset.client_id else None
    uploader = db.get(User, asset.uploaded_by_id)
    data = FileOut.model_validate(asset)
    data.project_name = project.name if project else None
    data.client_name = client.business_name if client else None
    data.uploader_name = uploader.display_name if uploader else None
    data.download_url = f"{settings.api_v1_prefix}/files/{asset.id}/download"
    return data


def _can_see(db, user: User, asset: FileAsset) -> bool:
    from app.core.authz import is_founder, is_founder_or_pm, is_project_member

    if asset.kind == "credential":
        return is_founder(user) or role_has_permission(user.role_key, Perm.CREDENTIALS_READ)
    if is_founder(user) or is_founder_or_pm(user):
        return True
    if asset.uploaded_by_id == user.id:
        return True
    if asset.project_id and is_project_member(db, user, asset.project_id):
        return True
    return False


def _can_mutate(db, user: User, asset: FileAsset) -> bool:
    from app.core.authz import is_founder

    if asset.kind == "credential":
        return is_founder(user) or role_has_permission(user.role_key, Perm.CREDENTIALS_WRITE)
    return is_founder(user) or asset.uploaded_by_id == user.id


@router.get("", response_model=list[FileOut])
def list_files(
    db: DbDep,
    user: CurrentUser,
    q: str | None = None,
    project_id: UUID | None = None,
    client_id: UUID | None = None,
    kind: str | None = None,
    limit: int = LimitQuery(50),
    before: datetime | None = Query(None, description="Cursor: created_at strictly before"),
):
    _require_read(user, kind)
    limit = clamp_limit(limit)
    stmt = select(FileAsset).where(FileAsset.deleted_at.is_(None))
    if project_id:
        stmt = stmt.where(FileAsset.project_id == project_id)
    if client_id:
        stmt = stmt.where(FileAsset.client_id == client_id)
    if kind:
        stmt = stmt.where(FileAsset.kind == kind)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                FileAsset.name.ilike(like),
                FileAsset.original_name.ilike(like),
                FileAsset.notes.ilike(like),
            )
        )
    # Over-fetch slightly then filter visibility; still hard-capped.
    stmt = apply_created_before_cursor(stmt, FileAsset, before).limit(limit)
    rows = [a for a in db.scalars(stmt).all() if _can_see(db, user, a)]
    return [_hydrate(db, a) for a in rows]


@router.get("/{file_id}", response_model=FileOut)
def get_file(file_id: UUID, db: DbDep, user: CurrentUser):
    from app.core.authz import not_found

    asset = db.get(FileAsset, file_id)
    if not asset or asset.deleted_at or not _can_see(db, user, asset):
        raise not_found("File")
    return _hydrate(db, asset)


@router.post("", response_model=FileOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    db: DbDep,
    user: CurrentUser,
    file: UploadFile = File(...),
    name: str | None = Form(None),
    kind: str = Form("asset"),
    notes: str | None = Form(None),
    project_id: UUID | None = Form(None),
    client_id: UUID | None = Form(None),
):
    _require_write(user, kind)
    original = store.sanitize_filename(file.filename or "upload.bin")
    if not store.extension_allowed(original):
        raise HTTPException(400, "File type not allowed")
    data = await file.read()
    if len(data) > store.MAX_UPLOAD_BYTES:
        raise HTTPException(400, "File exceeds 25MB limit")
    if not data:
        raise HTTPException(400, "Empty file")

    org = tenant_id(user)
    storage_key = store.build_storage_key(org, original)
    size = store.write_bytes(storage_key, data)
    display = store.sanitize_filename(name or original)

    asset = FileAsset(
        name=display,
        original_name=original,
        storage_key=storage_key,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=size,
        kind=kind or "asset",
        notes=notes,
        project_id=project_id,
        client_id=client_id,
        uploaded_by_id=user.id,
        org_id=org,
    )
    db.add(asset)
    db.flush()
    log_activity(
        db,
        actor=user,
        verb="uploaded",
        entity_type="file",
        entity_id=asset.id,
        project_id=asset.project_id,
        client_id=asset.client_id,
        summary=f"{user.display_name} uploaded “{asset.name}”",
    )
    audit(
        db,
        user=user,
        action="file.upload",
        entity_type="file",
        entity_id=asset.id,
        meta={"name": asset.name, "size": size, "kind": asset.kind},
    )
    db.commit()
    db.refresh(asset)
    return _hydrate(db, asset)


@router.patch("/{file_id}", response_model=FileOut)
def update_file(file_id: UUID, payload: FileUpdate, db: DbDep, user: CurrentUser):
    from app.core.authz import not_found

    asset = db.get(FileAsset, file_id)
    if not asset or asset.deleted_at or not _can_mutate(db, user, asset):
        raise not_found("File")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        data["name"] = store.sanitize_filename(data["name"])
    for k, v in data.items():
        setattr(asset, k, v)
    db.add(asset)
    audit(db, user=user, action="file.update", entity_type="file", entity_id=asset.id)
    db.commit()
    db.refresh(asset)
    return _hydrate(db, asset)


@router.get("/{file_id}/download")
def download_file(file_id: UUID, db: DbDep, user: CurrentUser):
    from app.core.authz import not_found

    asset = db.get(FileAsset, file_id)
    if not asset or asset.deleted_at or not _can_see(db, user, asset):
        raise not_found("File")
    try:
        path = store.read_path(asset.storage_key)
    except FileNotFoundError:
        raise not_found("File")
    audit(
        db,
        user=user,
        action="file.download",
        entity_type="file",
        entity_id=asset.id,
        meta={"name": asset.name},
    )
    db.commit()
    # Force download; never render HTML/SVG inline (stored XSS)
    media = "application/octet-stream"
    return FileResponse(
        path,
        media_type=media,
        filename=asset.original_name,
        content_disposition_type="attachment",
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(file_id: UUID, db: DbDep, user: CurrentUser):
    from app.core.authz import not_found

    asset = db.get(FileAsset, file_id)
    if not asset or asset.deleted_at or not _can_mutate(db, user, asset):
        raise not_found("File")
    asset.deleted_at = utcnow()
    db.add(asset)
    audit(db, user=user, action="file.delete", entity_type="file", entity_id=asset.id)
    db.commit()
    return None
