"""Create decision_results table

Revision ID: 0003_create_decision_results_table
Revises: 0002_create_historical_courses_tables
Create Date: 2026-10-22 16:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003_create_decision_results_table"
down_revision: str | None = "0002_create_historical_courses_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_type = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    op.create_table(
        "decision_results",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column(
            "analysis_id",
            sa.String(length=64),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pack_id", sa.String(length=64), nullable=False),
        sa.Column("decision_type", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("is_noul", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("selected_choice", sa.String(length=128), nullable=True),
        sa.Column("distribution", json_type, nullable=False),
        sa.Column("score_value", sa.Float(), nullable=True),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("evidence_ids", json_type, nullable=False),
        sa.Column(
            "model_version", sa.String(length=64), nullable=False, server_default="jev-pinned"
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_decision_results_analysis_id", "decision_results", ["analysis_id"])
    op.create_index("ix_decision_results_pack_id", "decision_results", ["pack_id"])
    op.create_index(
        "ix_decision_results_analysis_pack",
        "decision_results",
        ["analysis_id", "pack_id"],
    )


def downgrade() -> None:
    op.drop_table("decision_results")
