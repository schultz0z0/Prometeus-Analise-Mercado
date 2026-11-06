import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from prometeus.application.collect_market_evidence import CollectMarketEvidenceService
from prometeus.domain.analyses import Analysis
from prometeus.domain.collection_execution import CollectionExecutionPolicy
from prometeus.domain.configuration import AppSettings
from prometeus.domain.research import CourseResearchPlan, PlannedToolCall
from prometeus.infrastructure.apify.client import ApifyClient
from prometeus.infrastructure.apify.registry import ApifyActorRegistry
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository


async def main():
    settings = AppSettings()
    assert '@prometeus-collection-restore:' in settings.DATABASE_URL
    registry = ApifyActorRegistry.from_settings(settings)
    report = {'checked_at': datetime.now(UTC).isoformat(), 'probe_scope': 'one bounded Actor through persisted collector in restored clone'}

    async def response_hook(response):
        if response.status_code >= 400:
            await response.aread()
            try:
                error = response.json().get('error', {})
            except ValueError:
                error = {}
            report['provider_error'] = {'status': response.status_code, 'type': error.get('type'), 'message': str(error.get('message', '')).replace(settings.APIFY_TOKEN, '[redacted]')[:1200]}

    async with httpx.AsyncClient(timeout=40, event_hooks={'response': [response_hook]}) as http:
        response = await http.get(f'{settings.APIFY_BASE_URL}/actors/apify~google-search-scraper', headers={'Authorization': f'Bearer {settings.APIFY_TOKEN}'})
        response.raise_for_status()
        actor = response.json()['data']
        report['pricing_models'] = [p.get('pricingModel') for p in actor.get('pricingInfos', [])]
        report['default_run_options'] = actor.get('defaultRunOptions')
        engine = create_async_engine(settings.DATABASE_URL)
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            analysis = Analysis.create(tenant_id='ens', course_name='Start contract probe', correlation_id='contract-probe')
            await AnalysisRepository(session).save(analysis)
            await session.commit()
            plan = CourseResearchPlan(analysis_id=analysis.id, understanding_hash='contract-probe', budget_limit_usd=None, execution_policy=CollectionExecutionPolicy(), tool_calls=[PlannedToolCall(id='start-contract-probe', capability='google_search', query='site:fgv.br curso governança inteligência artificial', rationale='Diagnose real provider rejection', max_items=10)])
            client = ApifyClient(api_token=settings.APIFY_TOKEN, registry=registry, http_client=http)
            outcome = await CollectMarketEvidenceService(session, client, registry).collect(tenant_id='ens', plan=plan)
            report['completed_call_ids'] = outcome.completed_call_ids
            report['optional_failures'] = outcome.optional_failures
            report['observed_cost_usd'] = outcome.spent_usd
        await engine.dispose()
    print(json.dumps(report, ensure_ascii=True))

asyncio.run(main())
