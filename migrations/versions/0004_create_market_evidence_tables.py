"""Create research_plans and market_evidences tables

Revision ID: 0004_create_market_evidence_tables
Revises: 0003_create_decision_results_table
Create Date: 2026-10-22 16:25:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004_create_market_evidence_tables"
down_revision: str | None = "0003_create_decision_results_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_type = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    # 1. Tabela research_plans
    op.create_table(
        "research_plans",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column(
            "analysis_id",
            sa.String(length=64),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("cache_key", sa.String(length=128), nullable=False),
        sa.Column("enabled_sources", json_type, nullable=False),
        sa.Column("budget_limit_usd", sa.Float(), nullable=False, server_default="2.0"),
        sa.Column("spent_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("allocated_budget", json_type, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PLANNED"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_research_plans_analysis_id", "research_plans", ["analysis_id"])
    op.create_index("ix_research_plans_tenant_id", "research_plans", ["tenant_id"])
    op.create_index("ix_research_plans_cache_key", "research_plans", ["cache_key"])
    op.create_index(
        "ix_research_plans_analysis_cache",
        "research_plans",
        ["analysis_id", "cache_key"],
    )

    # 2. Tabela market_evidences
    op.create_table(
        "market_evidences",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column(
            "analysis_id",
            sa.String(length=64),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("evidence_type", sa.String(length=32), nullable=False),
        sa.Column("source_name", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.String(length=512), nullable=False),
        sa.Column("collector", sa.String(length=64), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("raw_payload", json_type, nullable=False),
        sa.Column("sanitized_data", json_type, nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "collected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_market_evidences_analysis_id", "market_evidences", ["analysis_id"])
    op.create_index("ix_market_evidences_evidence_type", "market_evidences", ["evidence_type"])
    op.create_index("ix_market_evidences_content_hash", "market_evidences", ["content_hash"])
    op.create_index(
        "ix_market_evidences_analysis_type",
        "market_evidences",
        ["analysis_id", "evidence_type"],
    )
    op.create_index(
        "ix_market_evidences_analysis_hash",
        "market_evidences",
        ["analysis_id", "content_hash"],
    )


def downgrade() -> None:
    op.drop_table("market_evidences")
    op.drop_table("research_plans")
