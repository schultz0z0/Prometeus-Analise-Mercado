import asyncio
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.dossier_verifier import DossierVerifier
from prometeus.application.offer_comparability import qualified_competitor_offer
from prometeus.application.synthesize_dossier import DossierSynthesisService
from prometeus.domain.configuration import AppSettings
from prometeus.domain.dossiers import DossierOutput
from prometeus.infrastructure.db.backup import BackupRestoreManager
from prometeus.infrastructure.db.models import AnalysisJobModel, AnalysisModel, MarketEvidenceModel, ResearchPlanModel, ToolRunAttemptModel, ToolRunModel


async def main():
    identifier = '9cb4f98e-60b5-46d9-998e-5ad81ebe7d86'
    art = Path('/app/var/collection-v2-verification')
    art.mkdir(parents=True, exist_ok=True)
    settings = AppSettings()
    engine = create_async_engine(settings.DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        analysis = await session.get(AnalysisModel, identifier)
        assert analysis.status == 'COMPLETED', analysis.status
        facts = await DossierSynthesisService(session, None).build_facts(identifier)
        key = Path(settings.AUTH_ADMIN_KEY_PATH).read_text(encoding='utf-8').strip()
        async with httpx.AsyncClient(base_url='http://api:8000', headers={'Authorization': f'Bearer {key}'}, timeout=40) as http:
            response = await http.get(f'/v1/analyses/{identifier}/dossier')
            response.raise_for_status()
            payload = response.json()
        dossier = DossierOutput.model_validate(payload)
        assert dossier.status == 'VERIFIED'
        issues = DossierVerifier().verify_presentation(dossier, facts, payload['presentation'], analysis.proposal_data)
        assert not issues, issues
        assert dossier.facts_hash == facts.compute_facts_hash()
        plans = list((await session.execute(select(ResearchPlanModel).where(ResearchPlanModel.analysis_id == identifier))).scalars())
        assert all(p.budget_limit_usd is None and p.plan_snapshot['execution_policy']['spending_mode'] == 'monitor_only' for p in plans)
        runs = list((await session.execute(select(ToolRunModel).where(ToolRunModel.analysis_id == identifier))).scalars())
        attempts = list((await session.execute(select(ToolRunAttemptModel).where(ToolRunAttemptModel.analysis_id == identifier))).scalars())
        assert all(1 <= a.attempt_index <= 4 for a in attempts)
        remote_ids = [a.provider_run_id for a in attempts if a.provider_run_id]
        assert len(remote_ids) == len(set(remote_ids))
        benchmark = payload['presentation']['competitive_benchmark']
        assert benchmark['monitored_total'] == 10 and len(benchmark['rows']) == 10
        assert benchmark['total_offers'] == sum(len(row.get('offers', [])) for row in benchmark['rows'])
        evidence_rows = list((await session.execute(select(MarketEvidenceModel).where(MarketEvidenceModel.analysis_id == identifier))).scalars())
        by_evidence_id = {row.id: row for row in evidence_rows}
        assert all(row.sanitized_data['_qualification']['qualification_version'] == 4 for row in evidence_rows)
        assert all(row.sanitized_data['_qualification']['component_versions']['projector'] == 'typed-projection-v3' for row in evidence_rows)
        assert all(row.sanitized_data['_qualification']['component_versions'].get('ad_projector') == 'ad-projection-v2' for row in evidence_rows if row.evidence_type == 'PAID_COMPETITION')
        competitors = {c['id']: c for c in analysis.proposal_data['_institution_context']['competitors']}
        for institution in benchmark['rows']:
            domains = competitors[institution['competitor_id']]['domains']
            for offer in institution['offers']:
                assert offer['relation'] in {'direct', 'adjacent', 'unclassified'}
                for evidence_id in offer['evidence_ids']:
                    evidence = by_evidence_id[evidence_id]
                    assert qualified_competitor_offer(evidence.sanitized_data['_qualification'], evidence.evidence_type)
                    host = (urlsplit(evidence.source_url).hostname or '').lower()
                    assert any(host == domain or host.endswith('.' + domain) for domain in domains), 'Course source must be official'
        assert not any(r.status in {'RUNNING', 'IN_DOUBT', 'RETRY_SCHEDULED'} for r in runs)
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
        assert preservation['human_decisions'] == 4 and preservation['course_outcomes'] == 4
        report = {
            'analysis_id': identifier, 'status': analysis.status, 'dossier_status': dossier.status,
            'recommendation': analysis.recommendation, 'final_presentation_gate': 'passed', 'facts_hash_verified': True,
            'plan_count': len(plans), 'tool_run_count': len(runs), 'run_statuses': dict(Counter(r.status for r in runs)),
            'attempt_count': len(attempts), 'max_attempt_index': max((a.attempt_index for a in attempts), default=0),
            'qualification_rows': len(evidence_rows), 'qualification_version': 4, 'projector_version': 'typed-projection-v3',
            'ad_projector_version': 'ad-projection-v2',
            'official_offer_sources_verified': True,
            'unclassified_offer_relations': sum(offer['relation'] == 'unclassified' for row in benchmark['rows'] for offer in row['offers']),
            'observed_cost_usd': round(sum(r.cost_usd for r in runs), 6),
            'benchmark': {key: benchmark.get(key) for key in ['monitored_total', 'searched_total', 'completed_total', 'blocked_total', 'institutions_with_offers', 'total_offers', 'coverage_complete']},
            'institutions': [{key: row.get(key) for key in ['name', 'execution_status', 'evidence_status', 'evidence_ids', 'failures']} for row in benchmark['rows']],
            'preservation': preservation,
            'duration_seconds': (analysis.updated_at - analysis.created_at).total_seconds(),
            'job_status': await session.scalar(select(AnalysisJobModel.status).where(AnalysisJobModel.analysis_id == identifier)),
        }
        (art / 'facts.json').write_text(json.dumps(asdict(facts), ensure_ascii=False, default=str, indent=2), encoding='utf-8')
        (art / 'dossier.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        (art / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    async with factory() as session:
        backup = await BackupRestoreManager(session).create_backup('/app/var/backups/collection-v2-2026-11-05/postcompletion.json')
        await session.commit()
        report['backup'] = {'format': backup.version, 'records': backup.total_records, 'sha256': backup.payload_sha256, 'attempt_rows': backup.table_counts['tool_run_attempts']}
    (art / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True))
    await engine.dispose()

asyncio.run(main())
