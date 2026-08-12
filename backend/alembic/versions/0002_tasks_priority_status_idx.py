"""Additive index for migration-over-data coverage.

Revision ID: 0002_tasks_priority_status_idx
Revises: 0001_initial
Create Date: 2026-08-12
"""

from __future__ import annotations

from alembic import op

revision = "0002_tasks_priority_status_idx"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Additive only — safe on populated tables.
    op.execute("CREATE INDEX IF NOT EXISTS ix_tasks_priority_status ON tasks (priority, status)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_tasks_priority_status")
