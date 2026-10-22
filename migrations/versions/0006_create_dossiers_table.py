"""Create dossiers table

Revision ID: 0006_create_dossiers_table
Revises: 0005_create_scoring_results_table
Create Date: 2026-10-22 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006_create_dossiers_table"
down_revision: str | None = "0005_create_scoring_results_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_type = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    op.create_table(
        "dossiers",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column(
            "analysis_id",
            sa.String(length=64),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("facts_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("sections", json_type, nullable=False),
        sa.Column("claims", json_type, nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_dossiers_analysis_id", "dossiers", ["analysis_id"], unique=True)
    op.create_index("ix_dossiers_status", "dossiers", ["status"])


def downgrade() -> None:
    op.drop_table("dossiers")
