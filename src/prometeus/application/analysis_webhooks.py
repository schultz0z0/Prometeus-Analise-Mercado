"""Outbox de eventos institucionais, persistida junto com cada transição relevante."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from urllib.parse import urlsplit

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from prometeus.domain.analyses import Analysis
from prometeus.domain.configuration import AppSettings, TenantConfig
from prometeus.domain.webhooks import WebhookEvent, WebhookEventType
from prometeus.infrastructure.db.models import (
    AnalysisModel,
    ConfigSnapshotModel,
    WebhookDeliveryModel,
)
from prometeus.infrastructure.webhooks.dispatcher import WebhookDispatcher


async def enqueue_analysis_event(
    session: AsyncSession, analysis: Analysis, settings: AppSettings
) -> int:
    event_type = {
        "COMPLETED": "analysis.completed",
        "FAILED": "analysis.failed",
        "BLOCKED": "analysis.blocked",
    }.get(analysis.status.value)
    if event_type is None:
        return 0
    snapshot = (
        await session.execute(
            select(ConfigSnapshotModel).where(ConfigSnapshotModel.analysis_id == analysis.id)
        )
    ).scalar_one_or_none()
    config = TenantConfig.model_validate(snapshot.tenant_config_snapshot) if snapshot else None
    target_url = (config.webhooks.target_url if config else None) or settings.WEBHOOK_TARGET_URL
    allowed = config.webhooks.events if config else []
    if not target_url or not settings.WEBHOOK_SECRET or (allowed and event_type not in allowed):
        return 0
    parsed = urlsplit(target_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Webhook institucional exige destino HTTPS válido.")
    event_id = (
        "evt_"
        + hashlib.sha256(f"{analysis.id}:{analysis.revision}:{event_type}".encode()).hexdigest()[
            :40
        ]
    )
    exists = await session.scalar(
        select(WebhookDeliveryModel.id).where(
            WebhookDeliveryModel.event_id == event_id, WebhookDeliveryModel.target_url == target_url
        )
    )
    if exists:
        return 0
    session.add(
        WebhookDeliveryModel(
            id=event_id,
            analysis_id=analysis.id,
            event_id=event_id,
            event_type=event_type,
            target_url=target_url,
            status="PENDING",
            payload={
                "analysis_id": analysis.id,
                "tenant_id": analysis.tenant_id,
                "status": analysis.status.value,
                "recommendation": analysis.recommendation.value
                if analysis.recommendation
                else None,
            },
            next_attempt_at=datetime.now(UTC),
        )
    )
    await session.flush()
    return 1


async def deliver_pending_webhooks(
    session: AsyncSession, settings: AppSettings, dispatcher: WebhookDispatcher | None = None
) -> int:
    if not settings.WEBHOOK_SECRET:
        return 0
    now = datetime.now(UTC)
    # O scheduler único e FOR UPDATE SKIP LOCKED impedem workers de disputar uma entrega.
    rows = list(
        (
            await session.execute(
                select(WebhookDeliveryModel)
                .where(
                    WebhookDeliveryModel.status.in_(["PENDING", "FAILED"]),
                    or_(
                        WebhookDeliveryModel.next_attempt_at.is_(None),
                        WebhookDeliveryModel.next_attempt_at <= now,
                    ),
                )
                .order_by(WebhookDeliveryModel.created_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
        ).scalars()
    )
    sender = dispatcher or WebhookDispatcher(
        session, secret=settings.WEBHOOK_SECRET, shadow_mode=settings.SHADOW_MODE
    )
    count = 0
    for row in rows:
        tenant_id = await session.scalar(
            select(AnalysisModel.tenant_id).where(AnalysisModel.id == row.analysis_id)
        )
        if tenant_id is None:
            continue
        event = WebhookEvent.create(
            WebhookEventType(row.event_type),
            row.analysis_id,
            tenant_id,
            row.payload,
            event_id=row.event_id,
        )
        await sender.dispatch(event, row.target_url)
        count += 1
    return count
