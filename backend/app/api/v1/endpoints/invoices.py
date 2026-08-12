from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.core.authz import is_founder, not_found, require_founder
from app.core.deps import CurrentUser, DbDep
from app.core.tenant import tenant_id
from app.db.base import utcnow
from app.models.client import Client
from app.models.invoice import Invoice
from app.schemas.misc import InvoiceOut
from app.services.activity import audit

router = APIRouter()


class InvoiceCreate(BaseModel):
    client_id: UUID
    project_id: UUID | None = None
    amount: Decimal
    tax: Decimal = Decimal("0")
    discount: Decimal = Decimal("0")
    currency: str = "INR"
    due_date: date | None = None
    status: str = "draft"
    payment_method: str | None = None
    notes: str | None = None


class InvoiceUpdate(BaseModel):
    amount: Decimal | None = None
    tax: Decimal | None = None
    discount: Decimal | None = None
    due_date: date | None = None
    status: str | None = None
    payment_method: str | None = None
    notes: str | None = None


def _out(db, inv: Invoice) -> InvoiceOut:
    client = db.get(Client, inv.client_id)
    item = InvoiceOut.model_validate(inv)
    item.client_name = client.business_name if client else None
    return item


def _next_number(db) -> str:
    count = db.scalar(select(func.count()).select_from(Invoice)) or 0
    return f"INV-{utcnow().year}-{count + 1:04d}"


@router.get("", response_model=list[InvoiceOut])
def list_invoices(db: DbDep, user: CurrentUser):
    require_founder(user)
    invoices = db.scalars(select(Invoice).where(Invoice.deleted_at.is_(None)).order_by(Invoice.created_at.desc())).all()
    return [_out(db, inv) for inv in invoices]


@router.post("", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice(payload: InvoiceCreate, db: DbDep, user: CurrentUser):
    require_founder(user)
    client = db.get(Client, payload.client_id)
    if not client or client.deleted_at:
        raise not_found("Client")
    inv = Invoice(
        number=_next_number(db),
        client_id=payload.client_id,
        project_id=payload.project_id,
        amount=payload.amount,
        tax=payload.tax,
        discount=payload.discount,
        currency=payload.currency,
        due_date=payload.due_date,
        issued_date=utcnow().date(),
        status=payload.status,
        payment_method=payload.payment_method,
        notes=payload.notes,
        org_id=tenant_id(user),
    )
    db.add(inv)
    audit(db, user=user, action="invoice.create", entity_type="invoice", entity_id=inv.id)
    db.commit()
    db.refresh(inv)
    return _out(db, inv)


@router.patch("/{invoice_id}", response_model=InvoiceOut)
def update_invoice(invoice_id: UUID, payload: InvoiceUpdate, db: DbDep, user: CurrentUser):
    if not is_founder(user):
        raise not_found("Invoice")
    inv = db.get(Invoice, invoice_id)
    if not inv or inv.deleted_at:
        raise not_found("Invoice")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(inv, k, v)
    db.add(inv)
    audit(db, user=user, action="invoice.update", entity_type="invoice", entity_id=inv.id)
    db.commit()
    db.refresh(inv)
    return _out(db, inv)
