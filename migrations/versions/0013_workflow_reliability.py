"""Transactional analysis jobs, optimistic revision and webhook retries."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "0013_workflow_reliability"
down_revision = "0012_sector_radar_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("analyses") as batch:
        batch.add_column(sa.Column("revision", sa.Integer(), nullable=False, server_default="1"))
        batch.add_column(sa.Column("idempotency_key", sa.String(255), nullable=True))
        batch.create_unique_constraint(
            "uq_analysis_tenant_idempotency", ["tenant_id", "idempotency_key"]
        )
    bind = op.get_bind()
    analyses = sa.table(
        "analyses",
        sa.column("id", sa.String()),
        sa.column("tenant_id", sa.String()),
        sa.column("idempotency_key", sa.String()),
        sa.column("proposal_data", sa.JSON()),
        sa.column("previous_analysis_id", sa.String()),
        sa.column("status", sa.String()),
        sa.column("created_at", sa.DateTime()),
    )
    seen: set[tuple[str, str]] = set()
    for row in bind.execute(
        sa.select(analyses).order_by(analyses.c.created_at, analyses.c.id)
    ).mappings():
        key = (row["proposal_data"] or {}).get("_idempotency_key")
        if (
            row["previous_analysis_id"] is None
            and isinstance(key, str)
            and 0 < len(key) <= 255
            and (row["tenant_id"], key) not in seen
        ):
            bind.execute(
                analyses.update().where(analyses.c.id == row["id"]).values(idempotency_key=key)
            )
            seen.add((row["tenant_id"], key))
    op.create_table(
        "analysis_jobs",
        sa.Column(
            "analysis_id",
            sa.String(64),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("correlation_id", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_token", sa.String(64)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_analysis_jobs_status", "analysis_jobs", ["status"])
    jobs = sa.table(
        "analysis_jobs",
        sa.column("analysis_id"),
        sa.column("correlation_id"),
        sa.column("status"),
        sa.column("attempt_count"),
        sa.column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(UTC)
    for row in bind.execute(
        sa.select(analyses.c.id).where(analyses.c.status.in_(["QUEUED", "RUNNING"]))
    ):
        bind.execute(
            jobs.insert().values(
                analysis_id=row.id,
                correlation_id="migration-recovery",
                status="PENDING",
                attempt_count=0,
                next_attempt_at=now,
                created_at=now,
            )
        )
    with op.batch_alter_table("webhook_deliveries") as batch:
        batch.add_column(sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True))
    webhook = sa.table(
        "webhook_deliveries", sa.column("id"), sa.column("event_id"), sa.column("target_url")
    )
    seen_events: set[tuple[str, str]] = set()
    for row in bind.execute(sa.select(webhook).order_by(webhook.c.id)).mappings():
        event_key = (row["event_id"], row["target_url"])
        if event_key in seen_events:
            # Preserva cada registro legado; desambigua somente o identificador técnico duplicado.
            identifier = (
                "legacy_"
                + hashlib.sha256(f"{row['event_id']}:{row['id']}".encode()).hexdigest()[:40]
            )
            bind.execute(
                webhook.update().where(webhook.c.id == row["id"]).values(event_id=identifier)
            )
        seen_events.add(event_key)
    with op.batch_alter_table("webhook_deliveries") as batch:
        batch.create_unique_constraint("uq_webhook_event_target", ["event_id", "target_url"])


def downgrade() -> None:
    bind = op.get_bind()
    uniques = sa.inspect(bind).get_unique_constraints("webhook_deliveries")
    with op.batch_alter_table("webhook_deliveries") as batch:
        if any(item["name"] == "uq_webhook_event_target" for item in uniques):
            batch.drop_constraint("uq_webhook_event_target", type_="unique")
        batch.drop_column("next_attempt_at")
    op.drop_table("analysis_jobs")
    with op.batch_alter_table("analyses") as batch:
        batch.drop_constraint("uq_analysis_tenant_idempotency", type_="unique")
        batch.drop_column("idempotency_key")
        batch.drop_column("revision")
