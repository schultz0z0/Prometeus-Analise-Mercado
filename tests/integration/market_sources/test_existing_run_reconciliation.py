from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.collect_market_evidence import (
    CollectMarketEvidenceService,
    RequiredSourceBlockedError,
)
from prometeus.application.recover_market_collection import CollectionRetryScheduled
from prometeus.domain.analyses import Analysis
from prometeus.domain.collection_execution import CollectionExecutionPolicy
from prometeus.domain.configuration import AppSettings
from prometeus.domain.research import CourseResearchPlan, PlannedToolCall
from prometeus.infrastructure.apify.client import ApifyClient
from prometeus.infrastructure.apify.registry import ApifyActorRegistry
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import (
    Base,
    MarketEvidenceModel,
    ToolRunAttemptModel,
    ToolRunModel,
)


@pytest.mark.asyncio
@pytest.mark.parametrize("eventual_success", [True, False])
async def test_partial_succeeded_dataset_is_archived_then_reconciled_without_repurchase(eventual_success):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    requests = []
    reads = 0
    rows = [{"title": f"Curso {i}", "url": f"https://school.test/{i}", "#debug": i}
            for i in range(2)]
    remote = {"id": "one-paid-run", "status": "SUCCEEDED", "defaultDatasetId": "paid-output",
              "buildNumber": "0.0.474", "usageTotalUsd": 0.02}

    def handler(request):
        nonlocal reads
        requests.append(request)
        if "/datasets/" in request.url.path:
            reads += 1
            return httpx.Response(200, json=rows if eventual_success and reads > 1 else rows[:1],
                                  headers={"X-Apify-Pagination-Total": "2"})
        return httpx.Response(200, json={"data": remote})

    registry = ApifyActorRegistry.from_settings(AppSettings(
        _env_file=None, APIFY_ACTOR_GOOGLE_SEARCH="apify/google-search-scraper@0.0.474"))
    client = ApifyClient(api_token="test-token", registry=registry,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            analysis = Analysis.create(tenant_id="ens", course_name="Curso", correlation_id="cs00")
            await AnalysisRepository(db).save(analysis)
            await db.commit()
            plan = CourseResearchPlan(analysis_id=analysis.id, understanding_hash="hash",
                budget_limit_usd=None, execution_policy=CollectionExecutionPolicy(),
                tool_calls=[PlannedToolCall(capability="google_search", query="curso", rationale="test")])
            service = CollectMarketEvidenceService(db, client, registry)
            with pytest.raises(CollectionRetryScheduled):
                await service.collect(tenant_id="ens", plan=plan)
            run = (await db.scalars(select(ToolRunModel))).one()
            attempt = (await db.scalars(select(ToolRunAttemptModel))).one()
            assert run.parameters["dataset_archive"]["items"][0]["raw_payload"] == rows[0]
            assert run.parameters["dataset_archive"]["retrieval_complete"] is False
            assert run.parameters["dataset_read_pending"] is True
            assert run.parameters["observation_status"] == "dataset_read_pending"
            assert run.parameters["dataset_read_failures"][0]["reason"] == "page_count_mismatch"
            assert attempt.diagnosis["dataset_read_failures"][0]["returned_items"] == 1
            assert await db.scalar(select(func.count()).select_from(MarketEvidenceModel)) == 0
            for index in range(3):
                attempt.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
                await db.commit()
                if eventual_success:
                    await service.collect(tenant_id="ens", plan=plan)
                    break
                with pytest.raises(CollectionRetryScheduled if index < 2 else RequiredSourceBlockedError):
                    await service.collect(tenant_id="ens", plan=plan)
            assert sum(r.method == "POST" for r in requests) == 1
            assert await db.scalar(select(func.count()).select_from(ToolRunAttemptModel)) == 1
            assert run.provider_run_id == "one-paid-run"
            assert run.cost_usd == pytest.approx(0.02)
            assert len(run.parameters["dataset_read_failures"]) == (1 if eventual_success else 4)
            assert run.parameters["dataset_archive"]["retrieval_complete"] is eventual_success
            if eventual_success:
                assert run.parameters["dataset_read_pending"] is False
                assert run.status == "SUCCEEDED"
                assert await db.scalar(select(func.count()).select_from(MarketEvidenceModel)) == 2
            else:
                assert run.status == "IN_DOUBT"
                assert attempt.diagnosis["reconciliation_attempts"] == 3
    finally:
        await client.aclose()
        await engine.dispose()
