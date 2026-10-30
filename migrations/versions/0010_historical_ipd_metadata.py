"""Add historical curriculum and explicit observation metadata for IPD.

Existing unknown cohort status/price units are preserved as unknown.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010_historical_ipd_metadata"
down_revision = "0009_dossier_presentation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "historical_courses", sa.Column("family", sa.String(64), nullable=False, server_default="")
    )
    op.add_column(
        "historical_courses",
        sa.Column("curriculum_text", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "historical_courses",
        sa.Column(
            "curriculum_modules",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "historical_funnel_records",
        sa.Column("price_period", sa.String(16), nullable=False, server_default="unknown"),
    )
    op.add_column(
        "historical_funnel_records",
        sa.Column("data_complete", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "historical_funnel_records",
        sa.Column("cohort_status", sa.String(32), nullable=False, server_default="UNKNOWN"),
    )


def downgrade() -> None:
    for column in ("cohort_status", "data_complete", "price_period"):
        op.drop_column("historical_funnel_records", column)
    for column in ("curriculum_modules", "curriculum_text", "family"):
        op.drop_column("historical_courses", column)
