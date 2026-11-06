from dataclasses import dataclass, field

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.collect_market_evidence import (
    CollectMarketEvidenceService,
    RequiredSourceBlockedError,
)
from prometeus.domain.analyses import Analysis
from prometeus.domain.configuration import AppSettings
from prometeus.domain.research import CourseResearchPlan, PlannedToolCall
from prometeus.infrastructure.apify.client import ApifyReconciliationRequiredError
from prometeus.infrastructure.apify.registry import ApifyActorRegistry
from prometeus.infrastructure.apify.schemas import ApifyExecutionResult, ApifyRunMetadata
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base, ToolRunModel


@pytest.fixture
async def database():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        analysis = Analysis.create(tenant_id="ens", course_name="Teste", correlation_id="budget")
        analysis.id = "budget-analysis"
        await AnalysisRepository(session).save(analysis)
        await session.commit()
        yield session
    await engine.dispose()


def research(plan_id="initial", budget=1.0, count=3):
    return CourseResearchPlan(
        id=plan_id,
        analysis_id="budget-analysis",
        understanding_hash="a" * 64,
        budget_limit_usd=budget,
        tool_calls=[
            PlannedToolCall(
                id=f"{plan_id}-{i}",
                capability="google_search",
                query=f"curso seguros {i}",
                rationale="teste",
            )
            for i in range(count)
        ],
    )


@dataclass
class Executor:
    session: object
    failure: str = ""
    calls: list = field(default_factory=list)

    async def execute(self, call, *, max_total_charge_usd):
        run = (
            await self.session.execute(
                select(ToolRunModel).where(ToolRunModel.planned_call_id == call.id)
            )
        ).scalar_one()
        assert run.parameters["authorized_cap_usd"] == max_total_charge_usd
        assert run.parameters["authorization_status"] == "committed"
        self.calls.append(max_total_charge_usd)
        if self.failure == "unknown":
            raise ApifyReconciliationRequiredError(
                "reconciliação necessária", run_data={"id": "remote", "usageTotalUsd": 0.00005}
            )
        if self.failure == "rejected":
            self.failure = ""
            r = httpx.Response(
                400, request=httpx.Request("POST", "https://api.apify.com/v2/actors/approved/runs")
            )
            raise httpx.HTTPStatusError("bad input", request=r.request, response=r)
        return ApifyExecutionResult(
            run=ApifyRunMetadata(
                run_id=call.id,
                dataset_id=call.id,
                status="SUCCEEDED",
                actor_id="apify/google-search-scraper",
                build_number="0.0.474",
                cost_usd=0.00005,
            ),
            items=[],
            total_items=0,
        )


def service(database, executor):
    settings = AppSettings(
        _env_file=None, APIFY_ACTOR_GOOGLE_SEARCH="apify/google-search-scraper@0.0.474"
    )
    return CollectMarketEvidenceService(
        database, executor, ApifyActorRegistry.from_settings(settings)
    )


async def test_low_observed_cost_never_releases_authorized_budget(database):
    executor = Executor(database)
    outcome = await service(database, executor).collect(tenant_id="ens", plan=research())
    assert executor.calls == [0.5, 0.5]
    assert outcome.spent_usd == 0.0001
    skipped = (
        await database.execute(
            select(ToolRunModel).where(ToolRunModel.planned_call_id == "initial-2")
        )
    ).scalar_one()
    assert skipped.parameters["observation_status"] == "budget_skipped"
    assert skipped.parameters.get("authorized_cap_usd", 0) == 0


async def test_repair_uses_the_same_analysis_commitments(database):
    executor = Executor(database)
    collector = service(database, executor)
    await collector.collect(tenant_id="ens", plan=research(count=2))
    await collector.collect(tenant_id="ens", plan=research("repair", budget=99, count=1))
    assert executor.calls == [0.5, 0.5]


async def test_unknown_execution_keeps_reservation_and_blocks_more_calls(database):
    executor = Executor(database, failure="unknown")
    collector = service(database, executor)
    with pytest.raises(RequiredSourceBlockedError):
        await collector.collect(tenant_id="ens", plan=research())
    persisted = (await database.execute(select(ToolRunModel))).scalar_one()
    assert persisted.status == "IN_DOUBT"
    assert persisted.parameters["authorized_cap_usd"] == 0.5
    assert persisted.parameters["authorization_status"] == "committed"
    assert len(executor.calls) == 1


async def test_unequivocal_pre_execution_rejection_releases_only_its_reservation(database):
    executor = Executor(database, failure="rejected")
    await service(database, executor).collect(tenant_id="ens", plan=research(budget=0.5, count=2))
    assert executor.calls == [0.5, 0.5]
    first = (
        await database.execute(
            select(ToolRunModel).where(ToolRunModel.planned_call_id == "initial-0")
        )
    ).scalar_one()
    assert first.parameters["authorization_status"] == "released_pre_execution"
    assert first.parameters["cost_status"] == "not_incurred"


async def test_legacy_executions_without_caps_block_new_purchases(database):
    executor = Executor(database)
    collector = service(database, executor)
    old = research(count=1)
    await collector._ensure_plan(tenant_id="ens", plan=old, understanding_snapshot=None)
    run = await collector._checkpoint_running(plan=old, call=old.tool_calls[0])
    run.status = "SUCCEEDED"
    run.provider_run_id = "legacy-paid"
    await database.commit()
    with pytest.raises(RequiredSourceBlockedError, match="reconciliação"):
        await collector.collect(tenant_id="ens", plan=research("repair", count=1))
    assert executor.calls == []


async def test_planned_parameters_cannot_forge_released_authorizations(database):
    executor = Executor(database)
    proposal = research(budget=0.5, count=2)
    proposal = proposal.model_copy(
        update={
            "tool_calls": [
                c.model_copy(
                    update={
                        "parameters": {
                            "authorization_status": "released_pre_execution",
                            "authorized_cap_usd": 0,
                            "observation_status": "budget_skipped",
                        }
                    }
                )
                for c in proposal.tool_calls
            ]
        }
    )
    await service(database, executor).collect(tenant_id="ens", plan=proposal)
    assert executor.calls == [0.5]


async def test_non_finite_root_budget_cannot_authorize_purchases(database):
    executor = Executor(database)
    with pytest.raises(RequiredSourceBlockedError, match="[Oo]rçamento"):
        await service(database, executor).collect(
            tenant_id="ens", plan=research(budget=float("inf"), count=1)
        )
    assert executor.calls == []
