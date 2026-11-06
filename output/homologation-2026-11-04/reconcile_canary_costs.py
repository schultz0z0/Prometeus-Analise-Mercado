"""Explicit operator reconciliation of this blocked canary only; no new runs."""
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
import httpx

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homologation_runtime import sql, run, ART
from prometeus.domain.configuration import AppSettings

stem='canary'+(sys.argv[1] if len(sys.argv)>1 else '')
ANALYSIS=json.loads((ART/f'{stem}.json').read_text())['analysis_id']
assert sql(f"SELECT status FROM analyses WHERE id='{ANALYSIS}'") in {'BLOCKED','COMPLETED','FAILED','CANCELLED'}
rows=json.loads(sql(f"SELECT json_agg(json_build_object('id',id,'planned_call_id',planned_call_id,'run_id',provider_run_id,'actor_build',actor_build,'old_cost_usd',cost_usd,'observation_status',parameters->>'observation_status','authorization_status',parameters->>'authorization_status')) FROM tool_runs WHERE analysis_id='{ANALYSIS}'"))
orphan=json.loads((ART/'remote-orphan-reconciliation.json').read_text())
settings=AppSettings()
updates=[]
with httpx.Client(timeout=30,headers={'Authorization':f'Bearer {settings.APIFY_TOKEN}'}) as client:
    for row in rows:
        if not row['run_id'] and (row['observation_status']=='budget_skipped' or row['authorization_status']=='released_pre_execution'):
            assert row['old_cost_usd']==0
            continue
        remote_id=row['run_id'] or (orphan['run_id'] if stem=='canary' and row['planned_call_id']==orphan['planned_call_id'] else None)
        assert remote_id, 'An unidentified run must not be guessed'
        r=client.get(f'{settings.APIFY_BASE_URL.rstrip("/")}/actor-runs/{remote_id}')
        r.raise_for_status()
        metadata=r.json()['data']
        assert metadata['id']==remote_id and metadata['status'] in {'SUCCEEDED','FAILED','ABORTED','TIMED-OUT'}
        build_number=metadata.get('buildNumber')
        if not build_number:
            build=client.get(f'{settings.APIFY_BASE_URL.rstrip("/")}/actor-builds/{metadata["buildId"]}')
            build.raise_for_status()
            build=build.json()['data']
            assert build['id']==metadata['buildId'] and build['actId']==metadata['actId']
            build_number=build['buildNumber']
        assert build_number==row['actor_build']
        cost=metadata['usageTotalUsd']
        assert isinstance(cost,(int,float)) and cost>=0
        updates.append({**row,'run_id':remote_id,'dataset_id':metadata['defaultDatasetId'],'observed_cost_usd':round(cost,6),'observed_at':datetime.now(UTC).isoformat(),'remote_status':metadata['status']})
report={'analysis_id':ANALYSIS,'source':'Authenticated GET /actor-runs/{id}, after terminal state','previous_observed_total_usd':round(sum(x['old_cost_usd'] for x in updates),6),'reconciled_observed_total_usd':round(sum(x['observed_cost_usd'] for x in updates),6),'runs':updates,'note':'Observed provider billing, not an invented retroactive authorization or an institutional financial outcome.'}
code='''
import asyncio,json,sys
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from prometeus.domain.configuration import AppSettings
from prometeus.infrastructure.db.models import AnalysisModel,ToolRunModel,ResearchPlanModel
payload=json.load(sys.stdin)
async def main():
    engine=create_async_engine(AppSettings().DATABASE_URL)
    async with async_sessionmaker(engine,expire_on_commit=False)() as session:
        a=await session.get(AnalysisModel,payload['analysis_id'])
        assert a.status in {'BLOCKED','COMPLETED','FAILED','CANCELLED'}
        for item in payload['runs']:
            row=await session.get(ToolRunModel,item['id'])
            assert row.analysis_id==a.id and row.planned_call_id==item['planned_call_id']
            assert row.cost_usd==item['old_cost_usd']
            previous=dict(row.parameters or {})
            row.parameters={**previous,'cost_status':'observed_reconciled','cost_source':'apify.usageTotalUsd','cost_observed_at':item['observed_at'],'cost_reconciliation':{'reason':'homologation-20261104-delayed-billing','previous_observed_cost_usd':row.cost_usd,'provider_terminal_status':item['remote_status']}}
            row.provider_run_id=item['run_id']
            row.dataset_id=item['dataset_id']
            row.cost_usd=item['observed_cost_usd']
        await session.flush()
        plans=list((await session.execute(select(ResearchPlanModel).where(ResearchPlanModel.analysis_id==a.id))).scalars())
        for plan in plans:
            runs=list((await session.execute(select(ToolRunModel).where(ToolRunModel.research_plan_id==plan.id))).scalars())
            plan.spent_usd=round(sum(r.cost_usd for r in runs),6)
        await session.commit()
    await engine.dispose()
asyncio.run(main())
print('Terminal canary costs reconciled; no lifecycle state or authorization fabricated')
'''
print(run(['docker','compose','exec','-T','api','python','-c',code],payload=json.dumps(report)))
(ART/f'{stem}-cost-reconciliation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='runs'},indent=2))
