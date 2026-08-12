import os

# App tests use SQLite unless TEST_DATABASE_URL overrides.
# Preserve a Postgres URL for migration round-trips (CI service / local Docker).
_incoming = os.environ.get("DATABASE_URL", "")
if not os.environ.get("MIGRATION_DATABASE_URL") and _incoming.startswith("postgresql"):
    os.environ["MIGRATION_DATABASE_URL"] = _incoming
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "sqlite:///./studio_sunny_hq.db")
