from sqlalchemy import JSON, Uuid

# Portable types: PostgreSQL in production, SQLite for local fallback.
GUID = Uuid(as_uuid=True)
JSONType = JSON
