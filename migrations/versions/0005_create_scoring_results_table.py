"""Create scoring_results table

Revision ID: 0005_create_scoring_results_table
Revises: 0004_create_market_evidence_tables
Create Date: 2026-10-22 16:38:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005_create_scoring_results_table"
down_revision: str | None = "0004_create_market_evidence_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_type = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    op.create_table(
        "scoring_results",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column(
            "analysis_id",
            sa.String(length=64),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("profile_id", sa.String(length=64), nullable=False),
        sa.Column("viability_score", sa.Float(), nullable=False),
        sa.Column("coverage_score", sa.Float(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("partial_score", sa.Float(), nullable=False),
        sa.Column("recommendation", sa.String(length=32), nullable=False),
        sa.Column("is_experimental", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("pillar_scores", json_type, nullable=False),
        sa.Column("gate_details", json_type, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_scoring_results_analysis_id", "scoring_results", ["analysis_id"], unique=True
    )
    op.create_index("ix_scoring_results_profile_id", "scoring_results", ["profile_id"])


def downgrade() -> None:
    op.drop_table("scoring_results")
