"""Add Atlas quest type and flags used by the verified drop subset."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "game_quests",
        sa.Column("quest_type", sa.String(length=32), nullable=False, server_default="unknown"),
    )
    op.add_column(
        "game_quests",
        sa.Column("flags_json", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("game_quests", "flags_json")
    op.drop_column("game_quests", "quest_type")
