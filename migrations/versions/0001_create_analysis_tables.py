"""Create analysis, analysis_steps, audit_events and config_snapshots tables

Revision ID: 0001_create_analysis_tables
Revises:
Create Date: 2026-10-22 15:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_create_analysis_tables"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tipo JSONB no PostgreSQL, com fallback para JSON no SQLite/outros
json_type = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    # 1. analyses
    op.create_table(
        "analyses",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("course_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="QUEUED"),
        sa.Column("recommendation", sa.String(length=32), nullable=True),
        sa.Column("proposal_data", json_type, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_analyses_tenant_id", "analyses", ["tenant_id"])
    op.create_index("ix_analyses_status", "analyses", ["status"])
    op.create_index("ix_analyses_tenant_created", "analyses", ["tenant_id", "created_at"])

    # 2. analysis_steps
    op.create_table(
        "analysis_steps",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column(
            "analysis_id",
            sa.String(length=64),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("output_summary", json_type, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_analysis_steps_analysis_id", "analysis_steps", ["analysis_id"])
    op.create_index(
        "ix_analysis_steps_analysis_step",
        "analysis_steps",
        ["analysis_id", "step_number"],
        unique=True,
    )

    # 3. audit_events
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column(
            "analysis_id",
            sa.String(length=64),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_audit_events_analysis_id", "audit_events", ["analysis_id"])
    op.create_index("ix_audit_events_correlation_id", "audit_events", ["correlation_id"])
    op.create_index(
        "ix_audit_events_analysis_created", "audit_events", ["analysis_id", "created_at"]
    )

    # 4. config_snapshots
    op.create_table(
        "config_snapshots",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column(
            "analysis_id",
            sa.String(length=64),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("scoring_profile_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_config_snapshot", json_type, nullable=False),
        sa.Column("scoring_profile_snapshot", json_type, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_config_snapshots_analysis_id", "config_snapshots", ["analysis_id"])


def downgrade() -> None:
    op.drop_table("config_snapshots")
    op.drop_table("audit_events")
    op.drop_table("analysis_steps")
    op.drop_table("analyses")
