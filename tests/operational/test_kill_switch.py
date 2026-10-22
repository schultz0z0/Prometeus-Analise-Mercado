"""Testes operacionais do Kill Switch e cabeçalhos de segurança HTTP."""

from unittest.mock import patch

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.domain.analyses import Analysis
from prometeus.entrypoints.rest.app import app
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base
from prometeus.infrastructure.db.session import get_db_session


@pytest.fixture
async def op_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def op_client(op_session: AsyncSession) -> httpx.AsyncClient:
    async def override_session():
        yield op_session

    app.dependency_overrides[get_db_session] = override_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_security_headers_present_on_all_responses(op_client: httpx.AsyncClient) -> None:
    resp = await op_client.get("/health/live")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"
    assert resp.headers.get("Content-Security-Policy") == "default-src 'self'"


@pytest.mark.asyncio
async def test_kill_switch_blocks_new_analyses_and_reanalyses(
    op_client: httpx.AsyncClient, op_session: AsyncSession
) -> None:
    repo = AnalysisRepository(op_session)
    existing = Analysis.create(
        tenant_id="ens",
        course_name="MBA em Sinistros Globais",
        correlation_id="corr-exist",
    )
    await repo.save(existing)
    await op_session.commit()

    # Com KILL_SWITCH_ACTIVE = True
    with patch("prometeus.entrypoints.rest.app.AppSettings") as MockSettings:
        instance = MockSettings.return_value
        instance.KILL_SWITCH_ACTIVE = True
        instance.SHADOW_MODE = False

        # 1. Criação de nova análise é recusada com HTTP 503
        resp_post = await op_client.post(
            "/v1/analyses",
            json={"course_name": "Curso Tentado Sob Kill Switch", "tenant_id": "ens"},
            headers={"Idempotency-Key": "key-kill-1"},
        )
        assert resp_post.status_code == 503
        assert "Kill switch operacional ativo" in resp_post.json()["detail"]

        # 2. Reanálise vinculada também é recusada com HTTP 503
        resp_re = await op_client.post(
            f"/v1/analyses/{existing.id}/reanalyze",
            json={"proposal_data": {"price": 1000.0}},
        )
        assert resp_re.status_code == 503
        assert "Kill switch operacional ativo" in resp_re.json()["detail"]

        # 3. Leitura e consulta de status continuam operacionais para suporte e auditoria
        resp_get = await op_client.get(f"/v1/analyses/{existing.id}/status")
        assert resp_get.status_code == 200
        assert resp_get.json()["analysis_id"] == existing.id

        resp_health = await op_client.get("/health/live")
        assert resp_health.status_code == 200


@pytest.mark.asyncio
async def test_kill_switch_inactive_allows_submissions(
    op_client: httpx.AsyncClient, op_session: AsyncSession
) -> None:
    with (
        patch("prometeus.entrypoints.rest.app.AppSettings") as MockSettings,
        patch("prometeus.entrypoints.rest.app.run_analysis_workflow.delay"),
    ):
        instance = MockSettings.return_value
        instance.KILL_SWITCH_ACTIVE = False
        instance.SHADOW_MODE = False

        resp = await op_client.post(
            "/v1/analyses",
            json={"course_name": "Curso Sob Operação Normal", "tenant_id": "ens"},
            headers={"Idempotency-Key": "key-norm-1"},
        )
        assert resp.status_code == 202
        assert resp.json()["status"] == "QUEUED"
