from sqlalchemy import inspect, text

from app.core.tenant import (
    ORG_ID_COMPACT,
    ORG_ID_HYPHEN,
    TENANT_TABLES,
    apply_rls,
    org_id_storage,
)


def ensure_schema(engine) -> None:
    """Add columns introduced after the first SQLite create_all (local demo)."""
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    org_id = org_id_storage(engine.dialect.name)

    with engine.begin() as conn:
        if "organizations" in tables:
            exists = conn.execute(
                text("SELECT 1 FROM organizations WHERE slug = :slug OR id IN (:a, :b)"),
                {"slug": "studio-sunny", "a": ORG_ID_HYPHEN, "b": ORG_ID_COMPACT},
            ).first()
            if not exists:
                conn.execute(
                    text(
                        "INSERT INTO organizations (id, name, slug, timezone, currency, created_at, updated_at) "
                        "VALUES (:id, :name, :slug, :tz, :cur, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                    ),
                    {
                        "id": org_id,
                        "name": "Studio Sunny",
                        "slug": "studio-sunny",
                        "tz": "Asia/Kolkata",
                        "cur": "INR",
                    },
                )
            org_cols = {c["name"] for c in insp.get_columns("organizations")}
            for col, ddl in [
                ("legal_name", "ALTER TABLE organizations ADD COLUMN legal_name VARCHAR(200)"),
                ("billing_entity", "ALTER TABLE organizations ADD COLUMN billing_entity VARCHAR(200)"),
                ("public_site", "ALTER TABLE organizations ADD COLUMN public_site VARCHAR(200)"),
                ("hq_domain", "ALTER TABLE organizations ADD COLUMN hq_domain VARCHAR(200)"),
                ("client_portal_domain", "ALTER TABLE organizations ADD COLUMN client_portal_domain VARCHAR(200)"),
                ("careers_domain", "ALTER TABLE organizations ADD COLUMN careers_domain VARCHAR(200)"),
                ("timezone", "ALTER TABLE organizations ADD COLUMN timezone VARCHAR(64) DEFAULT 'Asia/Kolkata'"),
                ("currency", "ALTER TABLE organizations ADD COLUMN currency VARCHAR(8) DEFAULT 'INR'"),
                ("permission_overrides", "ALTER TABLE organizations ADD COLUMN permission_overrides JSON"),
            ]:
                if col not in org_cols:
                    conn.execute(text(ddl))

        if "refresh_tokens" in tables:
            cols = {c["name"] for c in insp.get_columns("refresh_tokens")}
            if "family_id" not in cols:
                conn.execute(text("ALTER TABLE refresh_tokens ADD COLUMN family_id VARCHAR(36)"))
            if "replaced_by_id" not in cols:
                conn.execute(text("ALTER TABLE refresh_tokens ADD COLUMN replaced_by_id VARCHAR(36)"))

        if "users" in tables:
            cols = {c["name"] for c in insp.get_columns("users")}
            if "totp_secret" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN totp_secret VARCHAR(64)"))
            if "totp_enabled" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN totp_enabled BOOLEAN DEFAULT 0"))
            if "google_sub" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN google_sub VARCHAR(128)"))

        if "documents" in tables:
            cols = {c["name"] for c in insp.get_columns("documents")}
            if "yjs_state" not in cols:
                # SQLite: BLOB; Postgres: BYTEA — SQLAlchemy LargeBinary maps both
                conn.execute(text("ALTER TABLE documents ADD COLUMN yjs_state BLOB"))

        dialect = engine.dialect.name
        for table in TENANT_TABLES:
            if table not in tables:
                continue
            cols = {c["name"] for c in insp.get_columns(table)}
            if "org_id" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN org_id VARCHAR(36)"))
            # Postgres UUID columns reject '' — only compare empty string on SQLite/text storage.
            if dialect == "postgresql":
                conn.execute(
                    text(f"UPDATE {table} SET org_id = :oid WHERE org_id IS NULL"),
                    {"oid": org_id},
                )
            else:
                conn.execute(
                    text(f"UPDATE {table} SET org_id = :oid WHERE org_id IS NULL OR org_id = ''"),
                    {"oid": org_id},
                )

    apply_rls(engine)
