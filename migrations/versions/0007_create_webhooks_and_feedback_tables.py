"""Create webhooks, human decisions and course outcomes tables

Revision ID: 0007_create_webhooks_and_feedback_tables
Revises: 0006_create_dossiers_table
Create Date: 2026-10-22 17:35:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0007_create_webhooks_and_feedback_tables"
down_revision: str | None = "0006_create_dossiers_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_type = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    # 1. Adiciona previous_analysis_id na tabela analyses
    op.add_column(
        "analyses", sa.Column("previous_analysis_id", sa.String(length=64), nullable=True)
    )
    op.create_index("ix_analyses_previous_analysis_id", "analyses", ["previous_analysis_id"])

    # 2. Cria tabela human_decisions
    op.create_table(
        "human_decisions",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column(
            "analysis_id",
            sa.String(length=64),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("user_role", sa.String(length=64), nullable=False),
        sa.Column("decision", sa.String(length=64), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("adjustments", json_type, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_human_decisions_analysis_id", "human_decisions", ["analysis_id"])

    # 3. Cria tabela course_outcomes
    op.create_table(
        "course_outcomes",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column(
            "analysis_id",
            sa.String(length=64),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_course_id", sa.String(length=64), nullable=False),
        sa.Column("launch_date", sa.String(length=32), nullable=False),
        sa.Column("enrolled_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("leads_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("applicants_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revenue_brl", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_course_outcomes_analysis_id", "course_outcomes", ["analysis_id"])
    op.create_index("ix_course_outcomes_external_id", "course_outcomes", ["external_course_id"])

    # 4. Cria tabela webhook_deliveries
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column(
            "analysis_id",
            sa.String(length=64),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("target_url", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload", json_type, nullable=False),
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_webhook_deliveries_analysis_id", "webhook_deliveries", ["analysis_id"])
    op.create_index("ix_webhook_deliveries_event_id", "webhook_deliveries", ["event_id"])
    op.create_index("ix_webhook_deliveries_status", "webhook_deliveries", ["status"])
    op.create_index("ix_webhook_event_status", "webhook_deliveries", ["event_id", "status"])


def downgrade() -> None:
    op.drop_table("webhook_deliveries")
    op.drop_table("course_outcomes")
    op.drop_table("human_decisions")
    op.drop_index("ix_analyses_previous_analysis_id", table_name="analyses")
    op.drop_column("analyses", "previous_analysis_id")
