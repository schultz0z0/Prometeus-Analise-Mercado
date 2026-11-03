"""Add sector_radar_snapshots table for permanent sector ecosystem monitoring."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0012_sector_radar_snapshots"
down_revision = "0011_execution_envelopes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB, "postgresql")
    op.create_table(
        "sector_radar_snapshots",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="READY"),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("monitored_actors_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("covered_actors", json_type, nullable=False, server_default="[]"),
        sa.Column("signals", json_type, nullable=False, server_default="[]"),
        sa.Column("trending_themes", json_type, nullable=False, server_default="[]"),
        sa.Column("spent_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("config_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_sector_radar_snapshots_tenant_id", "sector_radar_snapshots", ["tenant_id"])
    op.create_index(
        "ix_sector_radar_tenant_collected",
        "sector_radar_snapshots",
        ["tenant_id", "collected_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_sector_radar_tenant_collected", table_name="sector_radar_snapshots")
    op.drop_index("ix_sector_radar_snapshots_tenant_id", table_name="sector_radar_snapshots")
    op.drop_table("sector_radar_snapshots")

