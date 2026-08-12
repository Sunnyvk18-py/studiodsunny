import time
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update

from app.core.authz import is_founder, is_founder_or_pm, require_founder, require_founder_or_pm
from app.core.config import settings
from app.core.deps import CurrentUser, DbDep
from app.core.permissions import Perm, permission_matrix, role_has_permission, set_permission_overrides
from app.core.tenant import STUDIO_SUNNY_ORG_ID, tenant_id
from app.db.base import utcnow
from app.models.organization import Organization
from app.models.template import Template
from app.realtime.hub import hub
from app.services.activity import audit

router = APIRouter()

# Redis/worker probe is live I/O — cache so settings page load is not a connectivity round-trip.
_INTEGRATIONS_PROBE_TTL_S = 30.0
_integrations_probe_cache: dict[str, object] = {"at": 0.0, "redis_ok": False, "worker_beat": None}


def _probe_redis_cached() -> tuple[bool, str | None]:
    now = time.monotonic()
    cached_at = float(_integrations_probe_cache["at"] or 0.0)
    if now - cached_at < _INTEGRATIONS_PROBE_TTL_S:
        return bool(_integrations_probe_cache["redis_ok"]), _integrations_probe_cache["worker_beat"]  # type: ignore[return-value]
    redis_ok = False
    worker_beat: str | None = None
    try:
        import redis as redis_lib

        r = redis_lib.from_url(settings.redis_url, socket_connect_timeout=0.4, socket_timeout=0.4)
        redis_ok = bool(r.ping())
        raw = r.get("hq:worker:heartbeat")
        if isinstance(raw, bytes):
            worker_beat = raw.decode()
        elif raw:
            worker_beat = str(raw)
    except Exception:
        redis_ok = False
        worker_beat = None
    _integrations_probe_cache.update({"at": now, "redis_ok": redis_ok, "worker_beat": worker_beat})
    return redis_ok, worker_beat


class OrgSettingsOut(BaseModel):
    id: UUID
    name: str
    slug: str
    notes: str | None = None
    legal_name: str | None = None
    billing_entity: str | None = None
    public_site: str | None = None
    hq_domain: str | None = None
    client_portal_domain: str | None = None
    careers_domain: str | None = None
    timezone: str = "Asia/Kolkata"
    currency: str = "INR"


class OrgSettingsUpdate(BaseModel):
    name: str | None = None
    notes: str | None = None
    legal_name: str | None = None
    billing_entity: str | None = None
    public_site: str | None = None
    hq_domain: str | None = None
    client_portal_domain: str | None = None
    careers_domain: str | None = None
    timezone: str | None = None
    currency: str | None = None


class PermissionOverridesUpdate(BaseModel):
    overrides: dict[str, list[str]] = Field(default_factory=dict)


class TemplateOut(BaseModel):
    id: UUID
    kind: str
    title: str
    description: str | None = None
    body: dict


class TemplateCreate(BaseModel):
    kind: str
    title: str
    description: str | None = None
    body: dict = Field(default_factory=dict)


class TemplateUpdate(BaseModel):
    kind: str | None = None
    title: str | None = None
    description: str | None = None
    body: dict | None = None


class IntegrationStatus(BaseModel):
    key: str
    label: str
    configured: bool
    detail: str
    docs_hint: str | None = None


DEFAULT_TEMPLATES = [
    {
        "kind": "project",
        "title": "Website delivery",
        "description": "Standard marketing site phases",
        "body": {
            "phases": ["Discovery", "Design", "Build", "QA", "Launch"],
            "default_tasks": ["Kickoff call", "Sitemap", "Design review", "Staging deploy", "Handoff"],
        },
    },
    {
        "kind": "task",
        "title": "Bug triage",
        "description": "Reproduce → fix → verify",
        "body": {"checklist": ["Reproduce", "Write failing note", "Fix", "Verify on staging", "Close"]},
    },
    {
        "kind": "onboarding",
        "title": "New hire week 1",
        "description": "Studio Sunny onboarding",
        "body": {
            "days": ["Accounts + HQ login", "Meet the pod", "Read handbook", "Shadow a standup", "First small task"]
        },
    },
    {
        "kind": "doc",
        "title": "Client brief",
        "description": "Kickoff brief skeleton",
        "body": {
            "content": {
                "type": "doc",
                "content": [
                    {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Goals"}]},
                    {"type": "paragraph", "content": [{"type": "text", "text": "What success looks like…"}]},
                    {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Scope"}]},
                    {"type": "paragraph", "content": [{"type": "text", "text": "In / out of scope…"}]},
                ],
            }
        },
    },
]


def _org(db) -> Organization:
    # Prefer slug — SQLite UUID storage can disagree with GUID literal identity on UPDATE
    org = db.scalar(select(Organization).where(Organization.slug == "studio-sunny"))
    if not org:
        org = db.get(Organization, STUDIO_SUNNY_ORG_ID)
    if not org:
        raise HTTPException(404, "Organization not found")
    return org


def _serialize_org(org: Organization) -> OrgSettingsOut:
    return OrgSettingsOut(
        id=org.id,
        name=org.name,
        slug=org.slug,
        notes=org.notes,
        legal_name=org.legal_name,
        billing_entity=org.billing_entity,
        public_site=org.public_site,
        hq_domain=org.hq_domain,
        client_portal_domain=org.client_portal_domain,
        careers_domain=org.careers_domain,
        timezone=org.timezone or "Asia/Kolkata",
        currency=org.currency or "INR",
    )


def _seed_templates(db, user) -> None:
    n = db.scalar(select(func.count()).select_from(Template).where(Template.deleted_at.is_(None))) or 0
    if n:
        return
    for t in DEFAULT_TEMPLATES:
        db.add(
            Template(
                kind=t["kind"],
                title=t["title"],
                description=t["description"],
                body=t["body"],
                created_by_id=user.id,
                org_id=tenant_id(user),
            )
        )
    db.commit()


@router.get("/settings", response_model=OrgSettingsOut)
def get_company_settings(db: DbDep, user: CurrentUser):
    require_founder(user)
    return _serialize_org(_org(db))


@router.patch("/settings", response_model=OrgSettingsOut)
def update_company_settings(payload: OrgSettingsUpdate, db: DbDep, user: CurrentUser):
    require_founder(user)
    org = _org(db)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(org, k, v)
    db.add(org)
    audit(db, user=user, action="org.settings.update", entity_type="organization", entity_id=org.id)
    db.commit()
    db.refresh(org)
    return _serialize_org(org)


@router.get("/permissions")
def get_permissions(db: DbDep, user: CurrentUser):
    require_founder(user)
    org = _org(db)
    set_permission_overrides(org.permission_overrides)
    return permission_matrix()


@router.put("/permissions/overrides")
def update_permission_overrides(payload: PermissionOverridesUpdate, db: DbDep, user: CurrentUser):
    require_founder(user)
    org = _org(db)
    # Never allow overrides that escalate into cash/audit/admin (PERMISSIONS.md)
    blocked = {
        Perm.AUDIT_READ.value,
        Perm.FINANCE_READ.value,
        Perm.FINANCE_WRITE.value,
        Perm.REPORTS_READ.value,
        Perm.SETTINGS_WRITE.value,
        Perm.PERMISSIONS_WRITE.value,
        Perm.CREDENTIALS_READ.value,
        Perm.CREDENTIALS_WRITE.value,
        Perm.ALL.value,
    }
    allowed = {p.value for p in Perm if p != Perm.ALL} - blocked
    cleaned: dict[str, list[str]] = {}
    for role, perms in payload.overrides.items():
        if role == "founder":
            continue
        cleaned[role] = sorted({p for p in perms if p in allowed})
    # Update by slug to avoid SQLite UUID identity mismatches on ORM flush
    db.execute(
        update(Organization).where(Organization.slug == "studio-sunny").values(permission_overrides=cleaned)
    )
    set_permission_overrides(cleaned)
    audit(db, user=user, action="org.permissions.update", entity_type="organization", entity_id=org.id)
    db.commit()
    return permission_matrix()


@router.get("/integrations", response_model=list[IntegrationStatus])
def list_integrations(user: CurrentUser):
    require_founder(user)
    redis_ok, worker_beat = _probe_redis_cached()
    _ = hub  # keep import used; chat hub shares redis

    return [
        IntegrationStatus(
            key="google_sso",
            label="Google SSO",
            configured=settings.google_oauth_enabled,
            detail="Connected" if settings.google_oauth_enabled else "Set GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET",
            docs_hint="GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI",
        ),
        IntegrationStatus(
            key="sentry",
            label="Sentry",
            configured=bool(settings.sentry_dsn),
            detail="DSN set" if settings.sentry_dsn else "Set SENTRY_DSN (+ NEXT_PUBLIC_SENTRY_DSN for web)",
            docs_hint="SENTRY_DSN, NEXT_PUBLIC_SENTRY_DSN",
        ),
        IntegrationStatus(
            key="posthog",
            label="PostHog",
            configured=bool(settings.posthog_api_key),
            detail="API key set" if settings.posthog_api_key else "Set POSTHOG_API_KEY (+ NEXT_PUBLIC_POSTHOG_KEY)",
            docs_hint="POSTHOG_API_KEY, NEXT_PUBLIC_POSTHOG_KEY",
        ),
        IntegrationStatus(
            key="otel",
            label="OpenTelemetry",
            configured=bool(settings.otel_exporter_otlp_endpoint),
            detail=settings.otel_exporter_otlp_endpoint or "Set OTEL_EXPORTER_OTLP_ENDPOINT",
            docs_hint="OTEL_EXPORTER_OTLP_ENDPOINT",
        ),
        IntegrationStatus(
            key="redis",
            label="Redis",
            configured=redis_ok,
            detail="Reachable" if redis_ok else "Cannot reach Redis (check REDIS_URL)",
            docs_hint="REDIS_URL",
        ),
        IntegrationStatus(
            key="arq_worker",
            label="Arq worker",
            configured=bool(worker_beat),
            detail=f"Last heartbeat: {worker_beat}" if worker_beat else "Run `npm run worker` or compose --profile workers",
            docs_hint="npm run worker · docker compose --profile workers up",
        ),
        IntegrationStatus(
            key="smtp",
            label="SMTP email",
            configured=bool(settings.smtp_host),
            detail="SMTP ready" if settings.smtp_host else "Invites log to console until SMTP_HOST is set",
            docs_hint="SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM",
        ),
    ]


@router.get("/templates", response_model=list[TemplateOut])
def list_templates(db: DbDep, user: CurrentUser, kind: str | None = None):
    require_founder_or_pm(user)
    _seed_templates(db, user)
    stmt = select(Template).where(Template.deleted_at.is_(None)).order_by(Template.kind, Template.title)
    if kind:
        stmt = stmt.where(Template.kind == kind)
    rows = db.scalars(stmt).all()
    return [
        TemplateOut(id=t.id, kind=t.kind, title=t.title, description=t.description, body=t.body or {}) for t in rows
    ]


@router.post("/templates", response_model=TemplateOut)
def create_template(payload: TemplateCreate, db: DbDep, user: CurrentUser):
    require_founder_or_pm(user)
    t = Template(
        kind=payload.kind,
        title=payload.title,
        description=payload.description,
        body=payload.body,
        created_by_id=user.id,
        org_id=tenant_id(user),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return TemplateOut(id=t.id, kind=t.kind, title=t.title, description=t.description, body=t.body or {})


@router.patch("/templates/{template_id}", response_model=TemplateOut)
def update_template(template_id: UUID, payload: TemplateUpdate, db: DbDep, user: CurrentUser):
    if not is_founder_or_pm(user):
        from app.core.authz import not_found

        raise not_found("Template")
    t = db.get(Template, template_id)
    if not t or t.deleted_at:
        from app.core.authz import not_found

        raise not_found("Template")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    db.add(t)
    db.commit()
    db.refresh(t)
    return TemplateOut(id=t.id, kind=t.kind, title=t.title, description=t.description, body=t.body or {})


@router.delete("/templates/{template_id}", status_code=204)
def delete_template(template_id: UUID, db: DbDep, user: CurrentUser):
    from app.core.authz import not_found

    if not is_founder(user):
        raise not_found("Template")
    t = db.get(Template, template_id)
    if not t or t.deleted_at:
        raise not_found("Template")
    t.deleted_at = utcnow()
    db.add(t)
    db.commit()
    return None
