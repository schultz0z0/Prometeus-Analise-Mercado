"""Create historical_courses and historical_funnel_records tables

Revision ID: 0002_create_historical_courses_tables
Revises: 0001_create_analysis_tables
Create Date: 2026-10-22 15:50:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_create_historical_courses_tables"
down_revision: str | None = "0001_create_analysis_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_type = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    # 1. historical_courses
    op.create_table(
        "historical_courses",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=False),
        sa.Column("modality", sa.String(length=64), nullable=False, server_default="online"),
        sa.Column("workload_hours", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("tags", json_type, nullable=False),
        sa.Column("target_audience", json_type, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_historical_courses_tenant_id", "historical_courses", ["tenant_id"])
    op.create_index("ix_historical_courses_external_id", "historical_courses", ["external_id"])
    op.create_index("ix_historical_courses_name", "historical_courses", ["name"])
    op.create_index("ix_historical_courses_category", "historical_courses", ["category"])
    op.create_index(
        "ix_historical_courses_tenant_ext",
        "historical_courses",
        ["tenant_id", "external_id"],
        unique=True,
    )

    # 2. historical_funnel_records
    op.create_table(
        "historical_funnel_records",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column(
            "course_id",
            sa.String(length=64),
            sa.ForeignKey("historical_courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_course_id", sa.String(length=64), nullable=False),
        sa.Column("period", sa.String(length=64), nullable=False),
        sa.Column("leads", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("applicants", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enrolled", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("conversion_lead_to_applicant", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "conversion_applicant_to_enrolled", sa.Float(), nullable=False, server_default="0.0"
        ),
        sa.Column("conversion_lead_to_enrolled", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("average_ticket_brl", sa.Float(), nullable=True),
        sa.Column("total_revenue_brl", sa.Float(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_historical_funnel_course_id", "historical_funnel_records", ["course_id"])
    op.create_index(
        "ix_historical_funnel_external_course_id",
        "historical_funnel_records",
        ["external_course_id"],
    )
    op.create_index("ix_historical_funnel_period", "historical_funnel_records", ["period"])
    op.create_index(
        "ix_historical_funnel_ext_period",
        "historical_funnel_records",
        ["external_course_id", "period"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("historical_funnel_records")
    op.drop_table("historical_courses")
