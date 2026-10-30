"""Add execution_envelopes table for model attempt audit and cache tracking.

Follows senior market intelligence plan (Phase 0, Task 0.3).
"""

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011_execution_envelopes"
down_revision = "0010_historical_ipd_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB, "postgresql")
    op.create_table(
        "execution_envelopes",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("analysis_id", sa.String(64), sa.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=True),
        sa.Column("tenant_id", sa.String(64), nullable=True),
        sa.Column("stage", sa.String(64), nullable=False),
        sa.Column("operation", sa.String(64), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("cache_key", sa.String(64), nullable=False),
        sa.Column("source_ids", json_type, nullable=False, server_default="[]"),
        sa.Column("component_versions", json_type, nullable=False, server_default="{}"),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("configured_model", sa.String(64), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("mode", sa.String(32), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("usage", json_type, nullable=True),
        sa.Column("cost_status", sa.String(32), nullable=False, server_default="UNAVAILABLE"),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("cost_source", sa.String(64), nullable=True),
        sa.Column("provider_attempts", sa.Integer(), nullable=True),
        sa.Column("decision_id", sa.String(64), nullable=True),
        sa.Column("result_kind", sa.String(64), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_execution_envelopes_analysis_stage", "execution_envelopes", ["analysis_id", "stage"])
    op.create_index("ix_execution_envelopes_cache", "execution_envelopes", ["cache_key"])
    op.create_index("ix_execution_envelopes_input_hash", "execution_envelopes", ["input_hash"])


def downgrade() -> None:
    op.drop_index("ix_execution_envelopes_input_hash", table_name="execution_envelopes")
    op.drop_index("ix_execution_envelopes_cache", table_name="execution_envelopes")
    op.drop_index("ix_execution_envelopes_analysis_stage", table_name="execution_envelopes")
    op.drop_table("execution_envelopes")

