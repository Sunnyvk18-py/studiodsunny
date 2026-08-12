from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

STUDIO_SUNNY_ORG_ID = UUID("3c8a1e90-7b2f-4d11-9c4a-0f6b2a8d1e55")
ORG_ID_HYPHEN = str(STUDIO_SUNNY_ORG_ID)
ORG_ID_COMPACT = ORG_ID_HYPHEN.replace("-", "")


def org_id_storage(dialect_name: str) -> str:
    """SQLite Uuid stores 32-char hex; Postgres keeps the canonical hyphenated form."""
    return ORG_ID_HYPHEN if dialect_name == "postgresql" else ORG_ID_COMPACT

TENANT_TABLES = (
    "users",
    "departments",
    "employees",
    "clients",
    "projects",
    "project_members",
    "project_milestones",
    "tasks",
    "task_comments",
    "invoices",
    "leads",
    "notifications",
    "activities",
    "chat_channels",
    "chat_channel_members",
    "chat_messages",
    "documents",
    "file_assets",
    "templates",
    "audit_logs",
    "refresh_tokens",
)


def tenant_id(user) -> UUID:
    return getattr(user, "org_id", None) or STUDIO_SUNNY_ORG_ID


def apply_tenant(db: Session, org_id: UUID | None) -> None:
    """SET LOCAL app.current_tenant for Postgres RLS. No-op on SQLite."""
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        return
    db.execute(
        text("SELECT set_config('app.current_tenant', :tid, true)"),
        {"tid": str(org_id) if org_id else ""},
    )


def apply_rls(engine) -> None:
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as conn:
        for table in TENANT_TABLES:
            exists = conn.execute(
                text("SELECT to_regclass(:name)"),
                {"name": f"public.{table}"},
            ).scalar()
            if not exists:
                continue
            conn.execute(text(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY'))
            conn.execute(text(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY'))
            conn.execute(text(f'DROP POLICY IF EXISTS tenant_isolation ON "{table}"'))
            conn.execute(
                text(
                    f"""
                    CREATE POLICY tenant_isolation ON "{table}"
                    USING (
                      COALESCE(current_setting('app.current_tenant', true), '') = ''
                      OR org_id::text = current_setting('app.current_tenant', true)
                    )
                    WITH CHECK (
                      COALESCE(current_setting('app.current_tenant', true), '') = ''
                      OR org_id::text = current_setting('app.current_tenant', true)
                    )
                    """
                )
            )
