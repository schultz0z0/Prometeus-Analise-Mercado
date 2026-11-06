"""Persist collection recovery attempts; preserve legacy policy snapshots."""

import sqlalchemy as sa
from alembic import op

revision = "0014_collection_attempts"
down_revision = "0013_workflow_reliability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("research_plans") as batch:
        batch.alter_column("budget_limit_usd", existing_type=sa.Float(), nullable=True)
    op.create_table(
        "tool_run_attempts",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "tool_run_id",
            sa.String(64),
            sa.ForeignKey("tool_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "analysis_id",
            sa.String(64),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("task_key", sa.String(64), nullable=False),
        sa.Column("attempt_index", sa.Integer(), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("actor_id", sa.String(255), nullable=False),
        sa.Column("actor_build", sa.String(32), nullable=False),
        sa.Column("provider_run_id", sa.String(128), unique=True),
        sa.Column("dataset_id", sa.String(128)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("diagnosis", sa.JSON(), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("cost_usd", sa.Float()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint(
            "analysis_id", "task_key", "attempt_index", name="uq_collection_task_attempt"
        ),
        sa.CheckConstraint(
            "attempt_index >= 1 AND attempt_index <= 4", name="ck_collection_attempt_range"
        ),
    )
    for column in ("tool_run_id", "analysis_id", "tenant_id"):
        op.create_index(f"ix_tool_run_attempts_{column}", "tool_run_attempts", [column])
    with op.batch_alter_table("market_evidences") as batch:
        batch.add_column(sa.Column("tool_run_attempt_id", sa.String(64), nullable=True))
        batch.create_foreign_key(
            "fk_evidence_collection_attempt",
            "tool_run_attempts",
            ["tool_run_attempt_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.execute(
        sa.text("SELECT count(*) FROM research_plans WHERE budget_limit_usd IS NULL")
    ).scalar():
        raise RuntimeError(
            "New monitoring-only plans require export before downgrade; no fictitious budget will be assigned."
        )
    with op.batch_alter_table("market_evidences") as batch:
        batch.drop_constraint("fk_evidence_collection_attempt", type_="foreignkey")
        batch.drop_column("tool_run_attempt_id")
    op.drop_table("tool_run_attempts")
    with op.batch_alter_table("research_plans") as batch:
        batch.alter_column("budget_limit_usd", existing_type=sa.Float(), nullable=False)
