import asyncio
import json
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.collect_market_evidence import CollectMarketEvidenceService
from prometeus.domain.analyses import Analysis
from prometeus.domain.configuration import AppSettings
from prometeus.domain.research import CourseResearchPlan, PlannedToolCall
from prometeus.infrastructure.apify.registry import ApifyActorRegistry
from prometeus.infrastructure.apify.schemas import ApifyExecutionResult, ApifyRunMetadata
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import ToolRunModel


async def main():
    engine=create_async_engine('postgresql+asyncpg://postgres:homologation-local-only@prometeus-homologation-restore:5432/homologation')
    factory=async_sessionmaker(engine,expire_on_commit=False)
    analysis_id=str(uuid.uuid4())
    calls=[]
    registry=ApifyActorRegistry.from_settings(AppSettings(_env_file=None,APIFY_ACTOR_GOOGLE_SEARCH='apify/google-search-scraper@0.0.474'))
    async with factory() as session:
        analysis=Analysis.create(tenant_id='ens',course_name='Concurrent budget test',correlation_id='qa')
        analysis.id=analysis_id
        await AnalysisRepository(session).save(analysis)
        await session.commit()
    class Executor:
        async def execute(self,call,*,max_total_charge_usd):
            async with factory() as independent:
                row=await independent.scalar(select(ToolRunModel).where(ToolRunModel.analysis_id==analysis_id,ToolRunModel.planned_call_id==call.id))
                assert row.parameters['authorized_cap_usd']==max_total_charge_usd
                assert row.parameters['authorization_status']=='committed'
            calls.append(max_total_charge_usd)
            await asyncio.sleep(0.05)
            return ApifyExecutionResult(run=ApifyRunMetadata(run_id=call.id,dataset_id=call.id,status='SUCCEEDED',actor_id='apify/google-search-scraper',build_number='0.0.474',cost_usd=0.00005),items=[],total_items=0)
    plans=[CourseResearchPlan(id=f'qa-{analysis_id}-{n}',analysis_id=analysis_id,understanding_hash='a'*64,budget_limit_usd=0.5,tool_calls=[PlannedToolCall(id=f'call-{n}',capability='google_search',query='test',rationale='test')]) for n in range(2)]
    async def collect(plan):
        async with factory() as session:
            await CollectMarketEvidenceService(session,Executor(),registry).collect(tenant_id='ens',plan=plan)
    await asyncio.gather(*(collect(plan) for plan in plans))
    async with factory() as session:
        rows=list((await session.execute(select(ToolRunModel).where(ToolRunModel.analysis_id==analysis_id))).scalars())
        caps=sum((Decimal(str(row.parameters.get('authorized_cap_usd',0))) for row in rows if row.parameters.get('authorization_status')=='committed'),Decimal('0'))
        assert caps==Decimal('0.5') and calls==[0.5]
        assert sum(row.parameters.get('observation_status')=='budget_skipped' for row in rows)==1
    await engine.dispose()
    print(json.dumps({'database':'isolated-PostgreSQL16','concurrent_collectors':2,'executed_calls':len(calls),'committed_cap_usd':str(caps),'root_budget_usd':'0.5','reservation_visible_before_executor':True,'result':'passed'}))


asyncio.run(main())
