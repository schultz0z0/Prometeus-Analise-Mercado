"""Audit the preserved real run when provider quota prevents completion."""
import asyncio
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.offer_comparability import qualified_competitor_offer
from prometeus.domain.configuration import AppSettings
from prometeus.infrastructure.db.backup import BackupRestoreManager
from prometeus.infrastructure.db.models import (
    AnalysisJobModel, AnalysisModel, AnalysisStepModel, DossierModel,
    MarketEvidenceModel, ResearchPlanModel, ToolRunAttemptModel, ToolRunModel,
)


async def main():
    identifier = '9cb4f98e-60b5-46d9-998e-5ad81ebe7d86'
    art = Path('/app/var/collection-v2-verification')
    art.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(AppSettings().DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        analysis = await session.get(AnalysisModel, identifier)
        assert analysis.status == 'BLOCKED'
        step = await session.scalar(select(AnalysisStepModel).where(AnalysisStepModel.analysis_id == identifier, AnalysisStepModel.step_number == 9))
        assert step.status == 'FAILED' and 'subscription_sharing_usage_limit_exceeded' in step.error_message
        assert await session.scalar(select(func.count()).select_from(DossierModel).where(DossierModel.analysis_id == identifier)) == 0
        job = await session.get(AnalysisJobModel, identifier)
        assert job.status == 'FINISHED' and not job.lease_token
        plans = list((await session.execute(select(ResearchPlanModel).where(ResearchPlanModel.analysis_id == identifier))).scalars())
        assert all(p.budget_limit_usd is None and p.plan_snapshot['execution_policy']['spending_mode'] == 'monitor_only' for p in plans)
        runs = list((await session.execute(select(ToolRunModel).where(ToolRunModel.analysis_id == identifier))).scalars())
        attempts = list((await session.execute(select(ToolRunAttemptModel).where(ToolRunAttemptModel.analysis_id == identifier))).scalars())
        assert not any(r.status in {'RUNNING', 'IN_DOUBT', 'RETRY_SCHEDULED'} for r in runs)
        assert not any(r.parameters.get('observation_status') == 'budget_skipped' for r in runs)
        assert all(1 <= a.attempt_index <= 4 for a in attempts)
        remote_ids = [a.provider_run_id for a in attempts if a.provider_run_id]
        assert len(remote_ids) == len(set(remote_ids))
        competitors = analysis.proposal_data['_institution_context']['competitors']
        searches = [r for r in runs if r.capability == 'google_search' and r.parameters.get('competitor_id')]
        assert {r.parameters['competitor_id'] for r in searches if r.status == 'SUCCEEDED'} == {c['id'] for c in competitors}
        rows = list((await session.execute(select(MarketEvidenceModel).where(MarketEvidenceModel.analysis_id == identifier))).scalars())
        v4 = [row for row in rows if row.sanitized_data.get('_qualification', {}).get('qualification_version') == 4]
        offers = [row for row in v4 if qualified_competitor_offer(row.sanitized_data['_qualification'], row.evidence_type)]
        preservation = {}
        for table, name in [('historical_courses', 'courses'), ('historical_funnel_records', 'funnels')]:
            row = (await session.execute(text(f"SELECT count(*), md5(string_agg(to_jsonb(t)::text, '' ORDER BY id)) FROM {table} t"))).one()
            preservation[name] = row[0]
            preservation[name + '_hash'] = row[1]
        preservation['old_dossiers_hash'] = await session.scalar(text("SELECT md5(string_agg(to_jsonb(t)::text, '' ORDER BY id)) FROM dossiers t WHERE analysis_id != :id"), {'id': identifier})
        preservation['human_decisions'] = await session.scalar(text('SELECT count(*) FROM human_decisions'))
        preservation['course_outcomes'] = await session.scalar(text('SELECT count(*) FROM course_outcomes'))
        assert preservation['courses'] == 33 and preservation['funnels'] == 66
        assert preservation['courses_hash'] == '1a78fa9b42b074976f2c1c64a97eca06'
        assert preservation['funnels_hash'] == 'b06fc7ba93d93e7a4dcbe7419709923a'
        assert preservation['old_dossiers_hash'] == '94236ffd06f20337a6f1655549e6016d'
        assert preservation['human_decisions'] == preservation['course_outcomes'] == 4
        report = {
            'checked_at': datetime.now(UTC).isoformat(), 'analysis_id': identifier,
            'status': analysis.status, 'job_status': job.status,
            'external_blocker': 'subscription_sharing_usage_limit_exceeded', 'dossier_published': False,
            'tool_runs': len(runs), 'tool_run_statuses': dict(Counter(r.status for r in runs)),
            'attempts': len(attempts), 'max_attempt_index': max(a.attempt_index for a in attempts),
            'observed_cost_usd': round(sum(r.cost_usd for r in runs), 6), 'cost_is_final_invoice': False,
            'configured_competitors': len(competitors), 'searched_competitors': len(searches),
            'competitor_runs': [{'competitor_id': r.parameters['competitor_id'], 'capability': r.capability, 'status': r.status, 'items': r.valid_items_count} for r in runs if r.parameters.get('competitor_id')],
            'evidence_rows': len(rows), 'qualification_v4_rows': len(v4),
            'qualification_unfinished': len(rows) - len(v4),
            'preliminary_offers_not_a_final_benchmark': [{'title': row.title, 'url': row.source_url, 'relation': row.sanitized_data['_qualification']['offer_comparability']['relation']} for row in offers],
            'preservation': preservation,
        }
    async with factory() as session:
        backup = await BackupRestoreManager(session).create_backup('/app/var/backups/collection-v2-2026-11-05/postdeployment.json')
        await session.commit()
        report['backup'] = {'format': backup.version, 'records': backup.total_records, 'sha256': backup.payload_sha256, 'attempt_rows': backup.table_counts['tool_run_attempts']}
    (art / 'blocked-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True))
    await engine.dispose()


asyncio.run(main())
