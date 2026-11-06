import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.collect_market_evidence import CollectMarketEvidenceService
from prometeus.application.recover_market_collection import CollectionRetryScheduled
from prometeus.domain.analyses import Analysis
from prometeus.domain.collection_execution import CollectionExecutionPolicy
from prometeus.domain.configuration import AppSettings
from prometeus.domain.research import CourseResearchPlan, PlannedToolCall
from prometeus.infrastructure.apify.registry import ApifyActorRegistry
from prometeus.infrastructure.apify.schemas import ApifyExecutionResult, ApifyRunMetadata
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.backup import BackupRestoreManager
from prometeus.infrastructure.db.models import HistoricalCourseModel, HistoricalFunnelModel, ToolRunAttemptModel


async def main():
    settings = AppSettings()
    assert '@prometeus-collection-restore:' in settings.DATABASE_URL, 'Checks restricted to restored clone'
    engine = create_async_engine(settings.DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    registry = ApifyActorRegistry.from_settings(AppSettings(_env_file=None, APIFY_ACTOR_GOOGLE_SEARCH='apify/google-search-scraper@0.0.473'))
    research = CourseResearchPlan(id='pg-concurrency-collection-v2', analysis_id='pg-concurrency-collection-v2', understanding_hash='test', budget_limit_usd=None, execution_policy=CollectionExecutionPolicy(), tool_calls=[PlannedToolCall(id='only-call', capability='google_search', query='test concurrency only', rationale='Offline executor concurrency check')])

    class Executor:
        calls = 0

        async def execute(self, call, *, max_total_charge_usd):
            assert max_total_charge_usd is None
            self.calls += 1
            await asyncio.sleep(0.1)
            return ApifyExecutionResult(run=ApifyRunMetadata(run_id='pg-offline-run', dataset_id='pg-offline-dataset', status='SUCCEEDED', actor_id='apify/google-search-scraper', build_number='0.0.473', cost_usd=0.02), items=[], total_items=0)

    executor = Executor()
    async with factory() as session:
        analysis = Analysis.create(tenant_id='ens', course_name='Offline collection lock check', correlation_id='clone')
        analysis.id = research.analysis_id
        await AnalysisRepository(session).save(analysis)
        await session.commit()
        collector = CollectMarketEvidenceService(session, executor, registry)
        await collector._ensure_plan(tenant_id='ens', plan=research, understanding_snapshot=None)

    async def collect():
        async with factory() as session:
            try:
                await CollectMarketEvidenceService(session, executor, registry).collect(tenant_id='ens', plan=research)
                return 'completed'
            except CollectionRetryScheduled:
                return 'inflight_preserved'

    outcomes = await asyncio.gather(collect(), collect())
    assert executor.calls == 1, (executor.calls, outcomes)
    async with factory() as session:
        attempts = await session.scalar(select(func.count()).select_from(ToolRunAttemptModel))
        assert attempts == 1
    async with factory() as session:
        manifest = await BackupRestoreManager(session).create_backup('/tmp/collection-v2-backup.json')
        await session.commit()
    async with factory() as session:
        report = await BackupRestoreManager(session).restore_backup('/tmp/collection-v2-backup.json', clean_existing=True)
        assert report['restored_counts']['tool_run_attempts'] == 1
        assert await session.scalar(select(func.count()).select_from(HistoricalCourseModel)) == 33
        assert await session.scalar(select(func.count()).select_from(HistoricalFunnelModel)) == 66
    print(json.dumps({'postgres_concurrency': 'passed', 'executor': 'offline-only', 'paid_posts_simulated': executor.calls, 'outcomes': outcomes, 'backup_restore': report['status'], 'backup_records': manifest.total_records, 'backup_attempts': manifest.table_counts['tool_run_attempts'], 'history_courses': 33, 'history_funnels': 66, 'checked_at': datetime.now(UTC).isoformat()}))
    await engine.dispose()

asyncio.run(main())
