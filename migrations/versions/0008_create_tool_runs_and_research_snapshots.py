"""Create tool runs and research snapshots.

Revision ID: 0008_create_tool_runs_and_research_snapshots
Revises: 0007_create_webhooks_and_feedback_tables
Create Date: 2026-10-23 20:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_create_tool_runs_and_research_snapshots"
down_revision: str | None = "0007_create_webhooks_and_feedback_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_type = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    op.add_column(
        "research_plans",
        sa.Column("understanding_snapshot", json_type, nullable=False, server_default="{}"),
    )
    op.add_column(
        "research_plans",
        sa.Column("plan_snapshot", json_type, nullable=False, server_default="{}"),
    )
    op.add_column(
        "research_plans",
        sa.Column("snapshot_hash", sa.String(length=64), nullable=False, server_default=""),
    )
    op.add_column(
        "research_plans",
        sa.Column("skill_snapshots", json_type, nullable=False, server_default="[]"),
    )

    op.create_table(
        "tool_runs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column(
            "analysis_id",
            sa.String(length=64),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "research_plan_id",
            sa.String(length=64),
            sa.ForeignKey("research_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("planned_call_id", sa.String(length=64), nullable=False),
        sa.Column("capability", sa.String(length=64), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.String(length=255), nullable=False),
        sa.Column("provider_run_id", sa.String(length=128), nullable=True),
        sa.Column("dataset_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("parameters", json_type, nullable=False, server_default="{}"),
        sa.Column("raw_items_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_items_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("research_plan_id", "planned_call_id", name="uq_tool_run_plan_call"),
    )
    op.create_index("ix_tool_runs_analysis_id", "tool_runs", ["analysis_id"])
    op.create_index("ix_tool_runs_research_plan_id", "tool_runs", ["research_plan_id"])
    op.create_index("ix_tool_runs_capability", "tool_runs", ["capability"])
    op.create_index("ix_tool_runs_provider_run_id", "tool_runs", ["provider_run_id"])
    op.create_index("ix_tool_runs_analysis_status", "tool_runs", ["analysis_id", "status"])

    op.add_column(
        "market_evidences",
        sa.Column(
            "tool_run_id",
            sa.String(length=64),
            sa.ForeignKey("tool_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_market_evidences_tool_run_id", "market_evidences", ["tool_run_id"])


def downgrade() -> None:
    op.drop_index("ix_market_evidences_tool_run_id", table_name="market_evidences")
    op.drop_column("market_evidences", "tool_run_id")
    op.drop_index("ix_tool_runs_analysis_status", table_name="tool_runs")
    op.drop_index("ix_tool_runs_provider_run_id", table_name="tool_runs")
    op.drop_index("ix_tool_runs_capability", table_name="tool_runs")
    op.drop_index("ix_tool_runs_research_plan_id", table_name="tool_runs")
    op.drop_index("ix_tool_runs_analysis_id", table_name="tool_runs")
    op.drop_table("tool_runs")
    op.drop_column("research_plans", "skill_snapshots")
    op.drop_column("research_plans", "snapshot_hash")
    op.drop_column("research_plans", "plan_snapshot")
    op.drop_column("research_plans", "understanding_snapshot")
