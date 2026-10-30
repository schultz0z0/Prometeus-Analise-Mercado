"""Add compatible typed presentation payload to dossiers.

Revision ID: 0009_dossier_presentation
Revises: 0008_create_tool_runs_and_research_snapshots
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009_dossier_presentation"
down_revision = "0008_create_tool_runs_and_research_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dossiers",
        sa.Column(
            "presentation",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("dossiers", "presentation")
