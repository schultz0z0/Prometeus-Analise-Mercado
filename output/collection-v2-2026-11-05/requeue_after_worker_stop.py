"""Maintenance only: run after confirming the old worker container has stopped."""
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.analysis_jobs import schedule_analysis_job_retry
from prometeus.domain.configuration import AppSettings
from prometeus.infrastructure.db.models import AnalysisJobModel, MarketEvidenceModel, ToolRunModel


async def main():
    identifier = '9cb4f98e-60b5-46d9-998e-5ad81ebe7d86'
    engine = create_async_engine(AppSettings().DATABASE_URL)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        active = await session.scalar(select(func.count()).select_from(ToolRunModel).where(
            ToolRunModel.analysis_id == identifier, ToolRunModel.status.in_(['RUNNING', 'IN_DOUBT', 'RETRY_SCHEDULED']),
        ))
        assert active == 0, 'Remote tasks must be terminal before maintenance'
        job = await session.scalar(select(AnalysisJobModel).where(AnalysisJobModel.analysis_id == identifier))
        assert job and job.status == 'RUNNING' and job.lease_token
        qualified = await session.scalar(select(func.count()).select_from(MarketEvidenceModel).where(
            MarketEvidenceModel.analysis_id == identifier,
            MarketEvidenceModel.sanitized_data['_qualification'].is_not(None),
        ))
        assert await schedule_analysis_job_retry(session, identifier, job.lease_token, datetime.now(UTC))
        report = {'analysis_id': identifier, 'reason': 'worker_update_for_course_focused_followups',
                  'at': datetime.now(UTC).isoformat(), 'job': 'PENDING',
                  'remote_active_tasks': active, 'qualified_rows_preserved': qualified}
        Path('/app/var/collection-v2-maintenance.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report))
    await engine.dispose()


asyncio.run(main())
