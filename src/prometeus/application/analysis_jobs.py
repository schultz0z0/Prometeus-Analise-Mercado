"""Publicação pós-commit e leases exclusivos para a outbox de análises."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from prometeus.infrastructure.db.models import AnalysisJobModel, AnalysisModel


async def publish_analysis_job(
    session: AsyncSession, analysis_id: str, publisher: Callable[[str, str], Any]
) -> bool:
    """A outbox já deve estar commitada. Falhas ficam persistidas para reconciliação."""
    now = datetime.now(UTC)
    token = uuid.uuid4().hex
    eligible = or_(
        and_(AnalysisJobModel.status == "PENDING", AnalysisJobModel.next_attempt_at <= now),
        and_(
            AnalysisJobModel.status.in_(["PUBLISHING", "PUBLISHED", "RUNNING"]),
            AnalysisJobModel.lease_expires_at <= now,
        ),
    )
    claim = await session.execute(
        update(AnalysisJobModel)
        .where(AnalysisJobModel.analysis_id == analysis_id, eligible)
        .values(
            status="PUBLISHING",
            lease_token=token,
            lease_expires_at=now + timedelta(seconds=60),
            attempt_count=AnalysisJobModel.attempt_count + 1,
        )
        .execution_options(synchronize_session=False)
    )
    await session.commit()
    if claim.rowcount != 1:  # type: ignore[attr-defined]
        return False
    job = (
        await session.execute(
            select(AnalysisJobModel)
            .where(AnalysisJobModel.analysis_id == analysis_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    status = await session.scalar(
        select(AnalysisModel.status).where(AnalysisModel.id == analysis_id)
    )
    if status in {"COMPLETED", "FAILED", "CANCELLED", "BLOCKED", "WAITING_FOR_INPUT"}:
        job.status = "FINISHED"
        job.lease_token = None
        job.lease_expires_at = None
        await session.commit()
        return False
    try:
        publisher(analysis_id, job.correlation_id)
    except Exception as error:
        await session.execute(
            update(AnalysisJobModel)
            .where(
                AnalysisJobModel.analysis_id == analysis_id, AnalysisJobModel.lease_token == token
            )
            .values(
                status="PENDING",
                lease_token=None,
                lease_expires_at=None,
                last_error=type(error).__name__,
                next_attempt_at=now + timedelta(seconds=min(300, 2 ** min(job.attempt_count, 8))),
            )
        )
        await session.commit()
        return False
    # Um consumidor imediato pode já ter adquirido outro lease; não o sobrescrever.
    await session.execute(
        update(AnalysisJobModel)
        .where(AnalysisJobModel.analysis_id == analysis_id, AnalysisJobModel.lease_token == token)
        .values(status="PUBLISHED", lease_expires_at=now + timedelta(minutes=5), last_error=None)
    )
    await session.commit()
    return True


async def claim_analysis_job(session: AsyncSession, analysis_id: str, token: str) -> bool:
    now = datetime.now(UTC)
    changed = await session.execute(
        update(AnalysisJobModel)
        .where(
            AnalysisJobModel.analysis_id == analysis_id,
            or_(
                and_(AnalysisJobModel.status == "PENDING", AnalysisJobModel.next_attempt_at <= now),
                AnalysisJobModel.status.in_(["PUBLISHING", "PUBLISHED"]),
                and_(
                    AnalysisJobModel.status == "RUNNING", AnalysisJobModel.lease_expires_at <= now
                ),
            ),
        )
        .values(status="RUNNING", lease_token=token, lease_expires_at=now + timedelta(minutes=5))
        .execution_options(synchronize_session=False)
    )
    await session.commit()
    return changed.rowcount == 1  # type: ignore[attr-defined,no-any-return]


async def schedule_analysis_job_retry(
    session: AsyncSession, analysis_id: str, token: str, next_attempt_at: datetime
) -> bool:
    """Libera o worker somente se o lease e a análise continuam ativos."""
    changed = await session.execute(
        update(AnalysisJobModel)
        .where(
            AnalysisJobModel.analysis_id == analysis_id,
            AnalysisJobModel.lease_token == token,
            AnalysisJobModel.status == "RUNNING",
            AnalysisJobModel.lease_expires_at > datetime.now(UTC),
            select(AnalysisModel.id).where(
                AnalysisModel.id == analysis_id, AnalysisModel.status == "RUNNING"
            ).exists(),
        )
        .values(
            status="PENDING", next_attempt_at=next_attempt_at,
            lease_token=None, lease_expires_at=None, last_error=None,
        )
        .execution_options(synchronize_session=False)
    )
    await session.commit()
    return changed.rowcount == 1  # type: ignore[attr-defined,no-any-return]


async def renew_analysis_job(session: AsyncSession, analysis_id: str, token: str) -> bool:
    result = await session.execute(
        update(AnalysisJobModel)
        .where(
            AnalysisJobModel.analysis_id == analysis_id,
            AnalysisJobModel.lease_token == token,
            AnalysisJobModel.status == "RUNNING",
        )
        .values(lease_expires_at=datetime.now(UTC) + timedelta(minutes=5))
    )
    await session.commit()
    return result.rowcount == 1  # type: ignore[attr-defined,no-any-return]


async def finish_analysis_job(session: AsyncSession, analysis_id: str, token: str) -> None:
    await session.execute(
        update(AnalysisJobModel)
        .where(AnalysisJobModel.analysis_id == analysis_id, AnalysisJobModel.lease_token == token)
        .values(status="FINISHED", lease_token=None, lease_expires_at=None)
    )
    await session.commit()


async def reconcile_analysis_jobs(
    session: AsyncSession, publisher: Callable[[str, str], Any]
) -> int:
    now = datetime.now(UTC)
    ids = list(
        (
            await session.execute(
                select(AnalysisJobModel.analysis_id)
                .where(
                    or_(
                        and_(
                            AnalysisJobModel.status == "PENDING",
                            AnalysisJobModel.next_attempt_at <= now,
                        ),
                        and_(
                            AnalysisJobModel.status.in_(["PUBLISHING", "PUBLISHED", "RUNNING"]),
                            AnalysisJobModel.lease_expires_at <= now,
                        ),
                    )
                )
                .order_by(AnalysisJobModel.next_attempt_at)
                .limit(100)
            )
        ).scalars()
    )
    count = 0
    for analysis_id in ids:
        count += int(await publish_analysis_job(session, analysis_id, publisher))
    return count
