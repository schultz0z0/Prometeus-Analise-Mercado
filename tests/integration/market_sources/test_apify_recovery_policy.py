from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.collect_market_evidence import CollectMarketEvidenceService
from prometeus.domain.analyses import Analysis
from prometeus.domain.collection_execution import CollectionExecutionPolicy
from prometeus.domain.configuration import AppSettings
from prometeus.domain.research import CourseResearchPlan, PlannedToolCall
from prometeus.infrastructure.apify.registry import ApifyActorRegistry
from prometeus.infrastructure.apify.schemas import ApifyExecutionResult, ApifyRunMetadata
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base, ToolRunAttemptModel, ToolRunModel


@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        analysis = Analysis.create(tenant_id="ens", course_name="Teste", correlation_id="recovery")
        analysis.id = "analysis"
        await AnalysisRepository(session).save(analysis)
        await session.commit()
        yield session
    await engine.dispose()


def plan(count=1, plan_id="initial"):
    return CourseResearchPlan(
        id=plan_id,
        analysis_id="analysis",
        understanding_hash="hash",
        budget_limit_usd=None,
        execution_policy=CollectionExecutionPolicy(),
        tool_calls=[
            PlannedToolCall(
                id=f"call-{i}", capability="google_search", query=f"curso {i}", rationale="teste"
            )
            for i in range(count)
        ],
    )


class Executor:
    def __init__(self, failures=0, status=429):
        self.calls = 0
        self.failures = failures
        self.status = status

    async def execute(self, call, *, max_total_charge_usd):
        assert max_total_charge_usd is None
        self.calls += 1
        if self.calls <= self.failures:
            response = httpx.Response(
                self.status,
                request=httpx.Request("POST", "https://api.apify.com/v2/actors/test/runs"),
            )
            raise httpx.HTTPStatusError(
                "provider rejected start", request=response.request, response=response
            )
        return ApifyExecutionResult(
            run=ApifyRunMetadata(
                run_id=f"remote-{self.calls}",
                dataset_id="dataset",
                status="SUCCEEDED",
                actor_id="apify/google-search-scraper",
                build_number="0.0.473",
                cost_usd=0.02,
            ),
            items=[],
            total_items=0,
        )


def service(db, executor):
    registry = ApifyActorRegistry.from_settings(
        AppSettings(
            _env_file=None,
            APIFY_ACTOR_GOOGLE_SEARCH="apify/google-search-scraper@0.0.473",
        )
    )
    return CollectMarketEvidenceService(db, executor, registry)


async def due(db):
    for attempt in (await db.execute(select(ToolRunAttemptModel))).scalars():
        attempt.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
    await db.commit()


@pytest.mark.asyncio
async def test_trends_retry_limits_native_browser_concurrency_and_persists_adjustment(db):
    from prometeus.application.recover_market_collection import CollectionRetryScheduled
    from prometeus.infrastructure.apify.client import ApifyActorFailedError

    class FailedBrowser(Executor):
        async def execute(self, call, *, max_total_charge_usd):
            self.calls += 1
            raise ApifyActorFailedError(
                message="browser launch timed out", run_id=f"trends-{self.calls}", status="FAILED",
                run_data={"status": "FAILED", "id": f"trends-{self.calls}"},
            )

    research = plan()
    research.tool_calls[0] = research.tool_calls[0].model_copy(update={
        "capability": "google_trends", "parameters": {"search_terms": ["curso IA", "LGPD"]},
    })
    registry = ApifyActorRegistry.from_settings(AppSettings(
        _env_file=None, APIFY_ACTOR_GOOGLE_TRENDS="apify/google-trends-scraper@0.0.143",
    ))
    executor = FailedBrowser()
    for _ in range(2):
        with pytest.raises(CollectionRetryScheduled):
            await CollectMarketEvidenceService(db, executor, registry).collect(tenant_id="ens", plan=research)
        await due(db)
    attempts = list((await db.execute(select(ToolRunAttemptModel).order_by(ToolRunAttemptModel.attempt_index))).scalars())
    assert "maxConcurrency" not in attempts[0].input_snapshot
    assert attempts[1].input_snapshot["maxConcurrency"] == 1
    assert attempts[1].input_snapshot["searchTerms"] == ["curso IA", "LGPD"]


@pytest.mark.asyncio
async def test_twelve_calls_continue_without_fixed_dollar_reservations(db):
    executor = Executor()
    result = await service(db, executor).collect(tenant_id="ens", plan=plan(12))
    assert executor.calls == 12
    assert len(result.completed_call_ids) == 12
    assert len((await db.execute(select(ToolRunAttemptModel))).scalars().all()) == 12


@pytest.mark.asyncio
async def test_rate_limit_recovery_survives_restart_and_stops_after_three_retries(db):
    from prometeus.application.recover_market_collection import CollectionRetryScheduled

    executor = Executor(failures=10)
    for attempt in range(1, 4):
        with pytest.raises(CollectionRetryScheduled):
            await service(db, executor).collect(tenant_id="ens", plan=plan())
        assert executor.calls == attempt
        await due(db)
    result = await service(db, executor).collect(tenant_id="ens", plan=plan())
    assert executor.calls == 4
    assert result.optional_failures == ["call-0"]
    await service(db, executor).collect(tenant_id="ens", plan=plan(plan_id="repair"))
    assert executor.calls == 4


@pytest.mark.asyncio
async def test_retry_success_preserves_failure_and_cost_once(db):
    from prometeus.application.recover_market_collection import CollectionRetryScheduled

    executor = Executor(failures=1)
    with pytest.raises(CollectionRetryScheduled):
        await service(db, executor).collect(tenant_id="ens", plan=plan())
    await due(db)
    outcome = await service(db, executor).collect(tenant_id="ens", plan=plan())
    assert outcome.completed_call_ids == ["call-0"]
    attempts = (
        (await db.execute(select(ToolRunAttemptModel).order_by(ToolRunAttemptModel.attempt_index)))
        .scalars()
        .all()
    )
    assert [a.status for a in attempts] == ["FAILED", "SUCCEEDED"]
    assert attempts[0].diagnosis["cause"] == "rate_limit"
    assert outcome.spent_usd == 0.02
    repeated = await service(db, executor).collect(tenant_id="ens", plan=plan())
    assert repeated.spent_usd == 0.02
    assert executor.calls == 2


@pytest.mark.asyncio
async def test_permanent_credentials_error_is_not_repeated(db):
    executor = Executor(failures=10, status=401)
    await service(db, executor).collect(tenant_id="ens", plan=plan())
    assert executor.calls == 1
    run = (await db.execute(select(ToolRunModel))).scalar_one()
    assert run.parameters["recovery_action"] == "operator_configuration_required"


@pytest.mark.asyncio
async def test_fresh_inflight_attempt_is_not_taken_over_by_another_collector(db):
    import asyncio

    from prometeus.application.recover_market_collection import CollectionRetryScheduled

    class Interrupted(Executor):
        async def execute(self, call, *, max_total_charge_usd):
            raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await service(db, Interrupted()).collect(tenant_id="ens", plan=plan())
    other = Executor()
    with pytest.raises(CollectionRetryScheduled):
        await service(db, other).collect(tenant_id="ens", plan=plan())
    assert other.calls == 0
    attempt = (await db.execute(select(ToolRunAttemptModel))).scalar_one()
    assert attempt.status == "RUNNING"
    assert not attempt.diagnosis.get("reconciliation_attempts")


@pytest.mark.asyncio
async def test_read_recovery_has_one_shared_budget_without_nested_http_retries(db):
    from prometeus.application.collect_market_evidence import RequiredSourceBlockedError
    from prometeus.application.recover_market_collection import CollectionRetryScheduled
    from prometeus.infrastructure.apify.client import ApifyClient

    counts = {"POST": 0, "dataset": 0}
    metadata = {"id": "single-paid-run", "status": "SUCCEEDED", "defaultDatasetId": "dataset", "buildNumber": "0.0.473", "usageTotalUsd": 0.02}

    def handler(request):
        if request.method == "POST":
            counts["POST"] += 1
            return httpx.Response(201, json={"data": metadata})
        if "/datasets/" in request.url.path:
            counts["dataset"] += 1
            return httpx.Response(502)
        return httpx.Response(200, json={"data": metadata})

    registry = service(db, Executor()).registry
    client = ApifyClient(api_token="test", registry=registry, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)), polling_interval_seconds=0)
    for expected in range(1, 4):
        with pytest.raises(CollectionRetryScheduled):
            await CollectMarketEvidenceService(db, client, registry).collect(tenant_id="ens", plan=plan())
        assert counts == {"POST": 1, "dataset": expected}
        await due(db)
    with pytest.raises(RequiredSourceBlockedError):
        await CollectMarketEvidenceService(db, client, registry).collect(tenant_id="ens", plan=plan())
    assert counts == {"POST": 1, "dataset": 4}


@pytest.mark.asyncio
async def test_dataset_provider_block_stops_after_three_retries_with_cost_preserved(db):
    from prometeus.application.recover_market_collection import CollectionRetryScheduled

    class BlockedDataset(Executor):
        async def execute(self, call, *, max_total_charge_usd):
            result = await super().execute(call, max_total_charge_usd=max_total_charge_usd)
            return result.model_copy(update={"items": [{"url": "https://fgv.br/curso", "error": "temporarily blocked"}], "total_items": 1})

    executor = BlockedDataset()
    for _ in range(3):
        with pytest.raises(CollectionRetryScheduled):
            await service(db, executor).collect(tenant_id="ens", plan=plan())
        await due(db)
    outcome = await service(db, executor).collect(tenant_id="ens", plan=plan())
    assert outcome.optional_failures == ["call-0"]
    assert outcome.spent_usd == pytest.approx(0.08)
    await service(db, executor).collect(tenant_id="ens", plan=plan())
    assert executor.calls == 4


@pytest.mark.asyncio
async def test_permanent_credentials_error_inside_dataset_does_not_buy_retries(db):
    class InvalidToken(Executor):
        async def execute(self, call, *, max_total_charge_usd):
            result = await super().execute(call, max_total_charge_usd=max_total_charge_usd)
            return result.model_copy(update={"items": [{"url": "https://fgv.br/curso", "error": "Unauthorized: invalid token", "httpStatusCode": 401}], "total_items": 1})

    executor = InvalidToken()
    outcome = await service(db, executor).collect(tenant_id="ens", plan=plan())
    assert outcome.optional_failures == ["call-0"]
    assert executor.calls == 1
    attempt = (await db.execute(select(ToolRunAttemptModel))).scalar_one()
    assert attempt.diagnosis["action"] == "operator_configuration_required"
    assert attempt.next_attempt_at is None
    assert attempt.cost_usd == 0.02


@pytest.mark.asyncio
async def test_uncertain_post_reconciles_three_times_without_nested_reads_or_repurchase(db):
    from prometeus.application.collect_market_evidence import RequiredSourceBlockedError
    from prometeus.application.recover_market_collection import CollectionRetryScheduled
    from prometeus.infrastructure.apify.client import ApifyClient

    counts = {"POST": 0, "GET": 0}

    def handler(request):
        counts[request.method] += 1
        return httpx.Response(502)

    registry = service(db, Executor()).registry
    client = ApifyClient(api_token="test", registry=registry, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)), polling_interval_seconds=0)
    for _ in range(3):
        with pytest.raises(CollectionRetryScheduled):
            await CollectMarketEvidenceService(db, client, registry).collect(tenant_id="ens", plan=plan())
        await due(db)
    with pytest.raises(RequiredSourceBlockedError):
        await CollectMarketEvidenceService(db, client, registry).collect(tenant_id="ens", plan=plan())
    assert counts == {"POST": 1, "GET": 3}
