from unittest.mock import patch

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.domain.webhooks import (
    WebhookDeliveryStatus,
    WebhookEvent,
    WebhookEventType,
)
from prometeus.entrypoints.rest.app import app
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base
from prometeus.infrastructure.db.session import get_db_session
from prometeus.infrastructure.webhooks.dispatcher import WebhookDispatcher


@pytest.fixture
async def shadow_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def shadow_client(shadow_session: AsyncSession) -> httpx.AsyncClient:
    async def override_session():
        yield shadow_session

    app.dependency_overrides[get_db_session] = override_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_tags_analysis_when_shadow_mode_active(
    shadow_client: httpx.AsyncClient, shadow_session: AsyncSession
) -> None:
    with (
        patch("prometeus.entrypoints.rest.app.AppSettings") as MockSettings,
        patch("prometeus.entrypoints.rest.app.run_analysis_workflow.delay"),
    ):
        instance = MockSettings.return_value
        instance.KILL_SWITCH_ACTIVE = False
        instance.SHADOW_MODE = True

        resp = await shadow_client.post(
            "/v1/analyses",
            json={"course_name": "Piloto Sob Shadow Mode ENS", "tenant_id": "ens"},
            headers={"Idempotency-Key": "key-shadow-1"},
        )
        assert resp.status_code == 202
        analysis_id = resp.json()["analysis_id"]

        repo = AnalysisRepository(shadow_session)
        created = await repo.get_by_id(analysis_id)
        assert created is not None
        assert created.proposal_data.get("_shadow_mode") is True


@pytest.mark.asyncio
async def test_webhook_dispatcher_shadow_mode_avoids_real_network_call(
    shadow_session: AsyncSession,
) -> None:
    event = WebhookEvent.create(
        event_type=WebhookEventType.ANALYSIS_COMPLETED,
        analysis_id="an-shadow-123",
        tenant_id="ens",
        payload={"score": 88.5, "recommendation": "APPROVED"},
    )

    # Inicializa dispatcher com shadow_mode=True
    dispatcher = WebhookDispatcher(
        db_session=shadow_session,
        shadow_mode=True,
    )

    # URL externa fictícia que causaria erro de conexão se chamada de verdade
    target_url = "https://crm.ens.edu.br/webhook-non-existent-endpoint"

    delivery = await dispatcher.dispatch(event=event, target_url=target_url)

    assert delivery.status == WebhookDeliveryStatus.SHADOW_DELIVERED.value
    assert delivery.response_code == 200
    assert "[SHADOW_MODE]" in (delivery.response_body or "")
    assert delivery.last_error is None
    assert delivery.attempt_count == 1
