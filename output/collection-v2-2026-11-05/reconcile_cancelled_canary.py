import asyncio
import json
import math
from datetime import UTC, datetime

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.domain.configuration import AppSettings
from prometeus.infrastructure.db.models import AnalysisModel, ResearchPlanModel, ToolRunAttemptModel, ToolRunModel


async def main():
    identifier = '8c609307-e515-4a14-aafe-5cf38c3c21f8'
    settings = AppSettings()
    engine = create_async_engine(settings.DATABASE_URL)
    report = {'analysis_id': identifier, 'action': 'cancelled-run reconciliation only', 'runs': []}
    async with async_sessionmaker(engine, expire_on_commit=False)() as session, httpx.AsyncClient(timeout=30, headers={'Authorization': f'Bearer {settings.APIFY_TOKEN}'}) as http:
        analysis = await session.get(AnalysisModel, identifier)
        assert analysis.status == 'CANCELLED'
        runs = list((await session.execute(select(ToolRunModel).where(ToolRunModel.analysis_id == identifier, ToolRunModel.status.in_(['RUNNING', 'IN_DOUBT'])))).scalars())
        for run in runs:
            assert run.provider_run_id
            response = await http.get(f'{settings.APIFY_BASE_URL}/actor-runs/{run.provider_run_id}')
            response.raise_for_status()
            data = response.json()['data']
            assert data['id'] == run.provider_run_id
            if data['status'] not in {'SUCCEEDED', 'FAILED', 'ABORTED', 'TIMED-OUT'}:
                aborted = await http.post(f'{settings.APIFY_BASE_URL}/actor-runs/{run.provider_run_id}/abort')
                aborted.raise_for_status()
                for _ in range(4):
                    response = await http.get(f'{settings.APIFY_BASE_URL}/actor-runs/{run.provider_run_id}')
                    response.raise_for_status()
                    data = response.json()['data']
                    if data['status'] in {'SUCCEEDED', 'FAILED', 'ABORTED', 'TIMED-OUT'}:
                        break
                    await asyncio.sleep(1)
            assert data['status'] in {'SUCCEEDED', 'FAILED', 'ABORTED', 'TIMED-OUT'}
            attempt = (await session.execute(select(ToolRunAttemptModel).where(ToolRunAttemptModel.tool_run_id == run.id).order_by(ToolRunAttemptModel.attempt_index.desc()))).scalars().first()
            cost = data.get('usageTotalUsd')
            valid = isinstance(cost, (int, float)) and not isinstance(cost, bool) and math.isfinite(cost) and cost >= 0
            if valid:
                attempt.cost_usd = cost
            attempt.status = 'CANCELLED'
            attempt.finished_at = datetime.now(UTC)
            attempt.next_attempt_at = None
            attempt.diagnosis = {**attempt.diagnosis, 'cause': 'analysis_cancelled', 'action': 'terminal_run_reconciled', 'provider_status': data['status'], 'reconciled_at': datetime.now(UTC).isoformat()}
            await session.flush()
            run.cost_usd = float(await session.scalar(select(func.sum(ToolRunAttemptModel.cost_usd)).where(ToolRunAttemptModel.tool_run_id == run.id)) or 0)
            run.status = 'CANCELLED'
            run.finished_at = datetime.now(UTC)
            run.error_code = 'cancelled_before_result_persistence'
            run.error_message = 'Análise cancelada; execução remota terminal reconciliada sem publicar evidências adicionais.'
            run.parameters = {**run.parameters, 'provider_status': data['status'], 'cost_status': 'observed_provisional' if valid else 'pending', 'cost_observed_at': datetime.now(UTC).isoformat(), 'cost_source': 'apify.usageTotalUsd', 'observation_status': 'cancelled_collection'}
            await session.flush()
            plan = await session.get(ResearchPlanModel, run.research_plan_id)
            plan.spent_usd = float(await session.scalar(select(func.sum(ToolRunModel.cost_usd)).where(ToolRunModel.research_plan_id == plan.id)) or 0)
            report['runs'].append({'run_id': run.provider_run_id, 'provider_status': data['status'], 'local_status': run.status, 'cost_usd_observed': run.cost_usd})
        await session.commit()
    await engine.dispose()
    print(json.dumps(report))

asyncio.run(main())
