"""Read-only review probes; in-memory DB/HTTP only, no paid requests."""

import asyncio
import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from sqlalchemy import select

from prometeus.domain.research import PlannedToolCall
from prometeus.domain.collection_execution import collection_task_key
from prometeus.infrastructure.apify.client import ApifyActorFailedError, ApifyClient
from prometeus.infrastructure.db.models import ToolRunAttemptModel, ToolRunModel, ResearchPlanModel


spec = importlib.util.spec_from_file_location("recovery_helpers", Path("tests/integration/market_sources/test_apify_recovery_policy.py"))
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)


class PaidFailureExecutor(helpers.Executor):
    async def execute(self, call, *, max_total_charge_usd):
        if self.calls == 0:
            self.calls += 1
            raise ApifyActorFailedError(run_id="paid-failed", status="FAILED", run_data={
                "id": "paid-failed", "status": "FAILED", "usageTotalUsd": 0.03,
            })
        return await super().execute(call, max_total_charge_usd=max_total_charge_usd)


async def cost_crash_probe():
    fixture = helpers.db.__wrapped__()
    db = await fixture.__anext__()
    try:
        executor = PaidFailureExecutor()
        try:
            await helpers.service(db, executor).collect(tenant_id="ens", plan=helpers.plan())
        except Exception as error:
            assert type(error).__name__ == "CollectionRetryScheduled"
        await helpers.due(db)
        service = helpers.service(db, executor)
        original = service._persist_result

        async def crash(**kwargs):
            result = await original(**kwargs)
            raise RuntimeError("simulated process loss after committed evidence checkpoint")

        service._persist_result = crash
        try:
            await service.collect(tenant_id="ens", plan=helpers.plan())
        except RuntimeError:
            pass
        await helpers.service(db, executor).collect(tenant_id="ens", plan=helpers.plan())
        attempts = (await db.execute(select(ToolRunAttemptModel))).scalars().all()
        run = (await db.execute(select(ToolRunModel))).scalar_one()
        plan = (await db.execute(select(ResearchPlanModel))).scalar_one()
        print("COST", {"attempt_total": sum(a.cost_usd or 0 for a in attempts), "run_total": run.cost_usd, "plan_total": plan.spent_usd, "run_status": run.status})
    finally:
        await fixture.aclose()


async def cancel_resume_probe():
    calls = []
    def handler(request):
        calls.append((request.method, request.url.path))
        return httpx.Response(200, json={"data": {"id": "remote-active", "status": "RUNNING"}})
    registry = helpers.service
    settings = helpers.AppSettings(_env_file=None, APIFY_ACTOR_GOOGLE_SEARCH="apify/google-search-scraper@0.0.473")
    async def inactive():
        return False
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = ApifyClient(api_token="test", registry=helpers.ApifyActorRegistry.from_settings(settings), http_client=http_client, cancellation_check=inactive)
        try:
            await client.resume(helpers.plan().tool_calls[0], run_id="remote-active")
        except asyncio.CancelledError:
            pass
    print("CANCEL_RESUME", calls)


def task_scope_probe():
    call = PlannedToolCall(capability="google_search", query="curso IA", rationale="scope", parameters={"country": "BR", "language": "pt"})
    other = call.model_copy(update={"parameters": {"country": "US", "language": "en"}})
    print("SCOPE_COLLISION", collection_task_key(call) == collection_task_key(other))


asyncio.run(cost_crash_probe())
asyncio.run(cancel_resume_probe())
task_scope_probe()
