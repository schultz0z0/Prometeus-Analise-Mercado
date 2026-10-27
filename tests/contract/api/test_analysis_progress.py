from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.domain.analyses import Analysis
from prometeus.entrypoints.rest.app import app
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base, ResearchPlanModel, ToolRunModel
from prometeus.infrastructure.db.session import get_db_session


@pytest.fixture
async def test_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def client(test_session: AsyncSession) -> httpx.AsyncClient:
    async def override_session():
        yield test_session

    app.dependency_overrides[get_db_session] = override_session
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as http_client:
        yield http_client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_progress_exposes_safe_tool_provenance_and_blocking_reason(
    client: httpx.AsyncClient,
    test_session: AsyncSession,
) -> None:
    analysis = Analysis.create(
        tenant_id="ens",
        course_name="Curso auditável",
        correlation_id="corr-progress",
    )
    analysis.start("corr-progress")
    analysis.block("corr-progress", reason="Fonte obrigatória meta_ads_library falhou")
    await AnalysisRepository(test_session).save(analysis)
    plan = ResearchPlanModel(
        id="plan-progress",
        analysis_id=analysis.id,
        tenant_id="ens",
        cache_key="hash",
        enabled_sources=["meta_ads_library"],
        budget_limit_usd=5.0,
        spent_usd=0.13,
        allocated_budget={},
        understanding_snapshot={},
        plan_snapshot={},
        snapshot_hash="hash",
        skill_snapshots=[],
        status="BLOCKED",
    )
    test_session.add(plan)
    test_session.add(
        ToolRunModel(
            id="run-progress",
            analysis_id=analysis.id,
            research_plan_id=plan.id,
            planned_call_id="call-meta",
            capability="meta_ads_library",
            query="curso seguros",
            required=True,
            provider="apify",
            actor_id="owner/actor",
            actor_build="1.2.3",
            status="FAILED",
            provider_run_id="apify-run-id",
            dataset_id="dataset-id",
            parameters={"secret_like_input": "must-not-leak"},
            raw_items_count=12,
            valid_items_count=9,
            cost_usd=0.13,
            error_code="http_500",
            error_message="Falha sanitizada",
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
        )
    )
    await test_session.commit()

    response = await client.get(f"/v1/analyses/{analysis.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "BLOCKED"
    assert payload["blocking"]["reason"] == "Fonte obrigatória meta_ads_library falhou"
    assert payload["tool_runs"] == [
        {
            "capability": "meta_ads_library",
            "query": "curso seguros",
            "required": True,
            "provider": "apify",
            "actor_id": "owner/actor",
            "actor_build": "1.2.3",
            "status": "FAILED",
            "run_id": "apify-run-id",
            "dataset_id": "dataset-id",
            "raw_items_count": 12,
            "valid_items_count": 9,
            "cost_usd": 0.13,
            "error_code": "http_500",
            "error_message": "Falha sanitizada",
            "started_at": payload["tool_runs"][0]["started_at"],
            "finished_at": payload["tool_runs"][0]["finished_at"],
        }
    ]
    assert "parameters" not in payload["tool_runs"][0]
