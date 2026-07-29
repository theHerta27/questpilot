"""Add optional pgvector storage when explicitly enabled."""

from __future__ import annotations

import os

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def enabled() -> bool:
    return os.getenv("PGVECTOR_ENABLED", "").lower() in {"1", "true", "yes"}


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql" and enabled():
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        op.execute("ALTER TABLE rag_chunks ADD COLUMN embedding_vector vector(96)")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql" and enabled():
        op.execute("ALTER TABLE rag_chunks DROP COLUMN IF EXISTS embedding_vector")
