from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, status
from sqlalchemy import func, select

from app.core.authz import is_founder, is_founder_or_pm, not_found, require_founder_or_pm
from app.core.deps import CurrentUser, DbDep
from app.core.tenant import tenant_id
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.project import Project
from app.schemas.client import ClientCreate, ClientOut, ClientUpdate
from app.services.activity import audit, log_activity
from app.utils import unique_slug

router = APIRouter()


def hydrate(db, c: Client, user) -> ClientOut:
    active = db.scalar(
        select(func.count()).select_from(Project).where(
            Project.client_id == c.id,
            Project.deleted_at.is_(None),
            Project.status.notin_(["completed", "paused"]),
        )
    ) or 0
    out = ClientOut.model_validate(c)
    out.active_projects = active
    # Cash figures: founder only (PERMISSIONS.md)
    if is_founder(user):
        pending = db.scalar(
            select(func.coalesce(func.sum(Invoice.amount), 0)).where(
                Invoice.client_id == c.id,
                Invoice.deleted_at.is_(None),
                Invoice.status.in_(["sent", "viewed", "partial", "overdue"]),
            )
        ) or 0
        out.pending_invoices = Decimal(pending)
    else:
        out.pending_invoices = None
    return out


@router.get("", response_model=list[ClientOut])
def list_clients(db: DbDep, user: CurrentUser, q: str | None = None, status_filter: str | None = None):
    require_founder_or_pm(user)
    stmt = select(Client).where(Client.deleted_at.is_(None)).order_by(Client.business_name)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(Client.business_name).like(like))
    if status_filter:
        stmt = stmt.where(Client.status == status_filter)
    return [hydrate(db, c, user) for c in db.scalars(stmt).all()]


@router.get("/{client_id}", response_model=ClientOut)
def get_client(client_id: UUID, db: DbDep, user: CurrentUser):
    if not is_founder_or_pm(user):
        raise not_found("Client")
    c = db.get(Client, client_id)
    if not c or c.deleted_at:
        raise not_found("Client")
    return hydrate(db, c, user)


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(payload: ClientCreate, db: DbDep, user: CurrentUser):
    require_founder_or_pm(user)
    client = Client(
        **payload.model_dump(),
        slug=unique_slug(db, Client, payload.business_name),
        org_id=tenant_id(user),
    )
    db.add(client)
    db.flush()
    log_activity(
        db,
        actor=user,
        verb="created",
        entity_type="client",
        entity_id=client.id,
        client_id=client.id,
        summary=f"{user.display_name} added client {client.business_name}",
    )
    audit(db, user=user, action="client.create", entity_type="client", entity_id=client.id)
    db.commit()
    db.refresh(client)
    return hydrate(db, client, user)


@router.patch("/{client_id}", response_model=ClientOut)
def update_client(client_id: UUID, payload: ClientUpdate, db: DbDep, user: CurrentUser):
    if not is_founder_or_pm(user):
        raise not_found("Client")
    c = db.get(Client, client_id)
    if not c or c.deleted_at:
        raise not_found("Client")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    db.add(c)
    log_activity(
        db,
        actor=user,
        verb="updated",
        entity_type="client",
        entity_id=c.id,
        client_id=c.id,
        summary=f"{user.display_name} updated {c.business_name}",
    )
    audit(db, user=user, action="client.update", entity_type="client", entity_id=c.id)
    db.commit()
    db.refresh(c)
    return hydrate(db, c, user)


@router.post("/{client_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
def archive_client(client_id: UUID, db: DbDep, user: CurrentUser):
    if not is_founder_or_pm(user):
        raise not_found("Client")
    from app.db.base import utcnow

    c = db.get(Client, client_id)
    if not c or c.deleted_at:
        raise not_found("Client")
    c.deleted_at = utcnow()
    db.add(c)
    audit(db, user=user, action="client.archive", entity_type="client", entity_id=c.id)
    log_activity(
        db,
        actor=user,
        verb="archived",
        entity_type="client",
        entity_id=c.id,
        client_id=c.id,
        summary=f"{user.display_name} archived {c.business_name}",
    )
    db.commit()
    return None
