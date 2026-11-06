"""Operator-authorized resumption of the preserved canary after quota reset."""
import asyncio
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.analysis_jobs import publish_analysis_job
from prometeus.domain.configuration import AppSettings
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import AnalysisJobModel, AnalysisModel, AnalysisStepModel, MarketEvidenceModel, ToolRunAttemptModel, ToolRunModel
from prometeus.infrastructure.factory import get_generative_model
from prometeus.workers.tasks import run_analysis_workflow


async def main():
    identifier = '9cb4f98e-60b5-46d9-998e-5ad81ebe7d86'
    settings = AppSettings()
    model = get_generative_model(settings)
    answer = await model.generate_text('Responda exatamente OK.', system_prompt='Teste de disponibilidade; responda somente OK.')
    assert answer.strip().rstrip('.') == 'OK', 'LLM availability check returned an unexpected response'
    engine = create_async_engine(settings.DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        owner = await session.scalar(select(AnalysisModel).where(AnalysisModel.id == identifier).with_for_update())
        assert owner and owner.tenant_id == 'ens' and owner.status == 'BLOCKED'
        step = await session.scalar(select(AnalysisStepModel).where(AnalysisStepModel.analysis_id == identifier, AnalysisStepModel.step_number == 9))
        assert step and step.status == 'FAILED' and 'subscription_sharing_usage_limit_exceeded' in step.error_message
        job = await session.get(AnalysisJobModel, identifier)
        assert job and job.status == 'FINISHED' and not job.lease_token
        assert not await session.scalar(select(func.count()).select_from(ToolRunModel).where(ToolRunModel.analysis_id == identifier, ToolRunModel.status.in_(['RUNNING', 'IN_DOUBT', 'RETRY_SCHEDULED'])))
        repository = AnalysisRepository(session)
        analysis = await repository.get_by_id(identifier)
        correlation_id = 'quota-reset-' + uuid.uuid4().hex
        analysis.resume(correlation_id=correlation_id, reason='Responsável confirmou renovação da cota; chamada real LLM confirmada antes da retomada.')
        await repository.save(analysis)
        job.status = 'PENDING'
        job.next_attempt_at = datetime.now(UTC)
        job.lease_token = None
        job.lease_expires_at = None
        job.last_error = None
        evidence_count = await session.scalar(select(func.count()).select_from(MarketEvidenceModel).where(MarketEvidenceModel.analysis_id == identifier))
        attempt_count = await session.scalar(select(func.count()).select_from(ToolRunAttemptModel).where(ToolRunAttemptModel.analysis_id == identifier))
        await session.commit()
        published = await publish_analysis_job(session, identifier, run_analysis_workflow.delay)
        report = {'analysis_id': identifier, 'resumed_at': datetime.now(UTC).isoformat(), 'llm_live_probe': 'passed',
                  'provider': settings.GEN_LLM_PROVIDER, 'model': getattr(model, 'model', None), 'published': published,
                  'evidence_rows_preserved': evidence_count, 'attempts_preserved': attempt_count}
        Path('/app/var/collection-v2-resumption.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report))
    await engine.dispose()


asyncio.run(main())
