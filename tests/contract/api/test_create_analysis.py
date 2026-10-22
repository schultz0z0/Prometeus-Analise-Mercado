from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.entrypoints.rest.app import app
from prometeus.infrastructure.db.models import Base
from prometeus.infrastructure.db.session import get_db_session


@pytest.fixture(autouse=True)
def mock_celery_delay() -> Generator[Any, None, None]:
    with patch("prometeus.entrypoints.rest.app.run_analysis_workflow.delay") as mock_task:
        yield mock_task


@pytest.fixture
async def test_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield test_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


async def test_health_live_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "live"
    assert data["product"] == "Prometeus"
    assert "version" in data
    assert "X-Correlation-ID" in resp.headers


async def test_create_analysis_missing_idempotency_key(client: AsyncClient) -> None:
    payload = {
        "course_name": "Gestão Avançada de Resseguros",
        "tenant_id": "ens",
        "proposal_data": {"price": 15000},
    }
    resp = await client.post("/v1/analyses", json=payload)
    assert resp.status_code == 400
    assert "Idempotency-Key" in resp.json()["detail"]


async def test_create_analysis_success_and_idempotency(client: AsyncClient) -> None:
    payload = {
        "course_name": "Certificação Profissional em Riscos Cibernéticos",
        "tenant_id": "ens",
        "proposal_data": {"modality": "online", "estimated_hours": 120},
    }
    headers = {
        "Idempotency-Key": "idemp-cyber-2026",
        "X-Correlation-ID": "test-corr-abc",
    }

    # Primeira chamada: cria nova análise
    resp1 = await client.post("/v1/analyses", json=payload, headers=headers)
    assert resp1.status_code == 202
    data1 = resp1.json()
    analysis_id = data1["analysis_id"]
    assert data1["status"] == "QUEUED"
    assert "aceita e enfileirada" in data1["message"]
    assert resp1.headers["X-Correlation-ID"] == "test-corr-abc"

    # Segunda chamada com a mesma chave: idempotente, retorna o mesmo analysis_id
    resp2 = await client.post("/v1/analyses", json=payload, headers=headers)
    assert resp2.status_code == 202
    data2 = resp2.json()
    assert data2["analysis_id"] == analysis_id
    assert "recuperada com sucesso" in data2["message"]

    # Consulta a análise criada
    resp3 = await client.get(f"/v1/analyses/{analysis_id}")
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["analysis_id"] == analysis_id
    assert data3["course_name"] == "Certificação Profissional em Riscos Cibernéticos"
    assert data3["status"] == "QUEUED"
    assert data3["recommendation"] is None
    assert len(data3["audit_events"]) == 1

    # Consulta o status
    resp4 = await client.get(f"/v1/analyses/{analysis_id}/status")
    assert resp4.status_code == 200
    data4 = resp4.json()
    assert data4["analysis_id"] == analysis_id
    assert data4["status"] == "QUEUED"
    assert data4["recommendation"] is None
