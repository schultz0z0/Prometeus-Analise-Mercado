"""Add dossier_area_reviews table for departmental governance in the CMS Dossier Revisions tab."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0013_dossier_area_reviews"
down_revision = "0012_sector_radar_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dossier_area_reviews",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "analysis_id",
            sa.String(64),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("area", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("reviewer_name", sa.String(128), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False, server_default=""),
        sa.Column("version_label", sa.String(32), nullable=False, server_default="v1.1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_dossier_area_reviews_analysis_id", "dossier_area_reviews", ["analysis_id"])
    op.create_index("ix_dossier_area_reviews_tenant_id", "dossier_area_reviews", ["tenant_id"])
    op.create_index(
        "ix_dossier_area_reviews_analysis_area",
        "dossier_area_reviews",
        ["analysis_id", "area"],
    )


def downgrade() -> None:
    op.drop_index("ix_dossier_area_reviews_analysis_area", table_name="dossier_area_reviews")
    op.drop_index("ix_dossier_area_reviews_tenant_id", table_name="dossier_area_reviews")
    op.drop_index("ix_dossier_area_reviews_analysis_id", table_name="dossier_area_reviews")
    op.drop_table("dossier_area_reviews")
