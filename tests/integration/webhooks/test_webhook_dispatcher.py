"""Testes de integração para WebhookDispatcher, assinatura HMAC, retries e dead-letter."""

import json
import time

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.domain.analyses import Analysis
from prometeus.domain.webhooks import (
    WebhookDeliveryStatus,
    WebhookEvent,
    WebhookEventType,
    compute_webhook_signature,
    verify_webhook_signature,
)
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base
from prometeus.infrastructure.webhooks.dispatcher import WebhookDispatcher


@pytest.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


def test_hmac_signature_generation_and_verification() -> None:
    secret = "test-secret-key-123"
    timestamp = int(time.time())
    payload = json.dumps({"course": "MBA em Sinistros", "score": 85.0})

    sig = compute_webhook_signature(secret, timestamp, payload)
    assert len(sig) == 64

    # Validação correta
    assert verify_webhook_signature(secret, sig, timestamp, payload) is True
    # Validação no formato header t=...,v1=...
    header_val = f"t={timestamp},v1={sig}"
    assert verify_webhook_signature(secret, header_val, timestamp, payload) is True

    # Replay attack: timestamp muito antigo (> 300s)
    old_ts = timestamp - 400
    assert verify_webhook_signature(secret, sig, old_ts, payload) is False

    # Payload adulterado
    tampered = json.dumps({"course": "MBA em Sinistros", "score": 99.9})
    assert verify_webhook_signature(secret, sig, timestamp, tampered) is False


@pytest.mark.asyncio
async def test_webhook_dispatcher_successful_delivery(db_session: AsyncSession) -> None:
    repo = AnalysisRepository(db_session)
    analysis = Analysis.create(tenant_id="ens", course_name="MBA em Riscos", correlation_id="c1")
    await repo.save(analysis)
    await db_session.commit()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert "X-Prometeus-Signature" in request.headers
        assert "X-Prometeus-Timestamp" in request.headers
        assert "X-Prometeus-Event-ID" in request.headers
        return httpx.Response(200, json={"received": True})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    dispatcher = WebhookDispatcher(db_session, secret="sec-key", http_client=mock_client)

    event = WebhookEvent.create(
        event_type=WebhookEventType.ANALYSIS_COMPLETED,
        analysis_id=analysis.id,
        tenant_id="ens",
        payload={"viability_score": 88.0, "recommendation": "APPROVED"},
    )

    delivery = await dispatcher.dispatch(event, "https://ens.edu.br/webhook/market-intel")
    assert delivery.status == WebhookDeliveryStatus.DELIVERED.value
    assert delivery.attempt_count == 1
    assert delivery.response_code == 200


@pytest.mark.asyncio
async def test_webhook_dispatcher_retries_and_dead_letter(db_session: AsyncSession) -> None:
    repo = AnalysisRepository(db_session)
    analysis = Analysis.create(tenant_id="ens", course_name="MBA em Sinistros", correlation_id="c2")
    await repo.save(analysis)
    await db_session.commit()

    # Simula falha constante (HTTP 503)
    def mock_failure(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="Service Unavailable")

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_failure))
    dispatcher = WebhookDispatcher(
        db_session,
        secret="sec-key",
        max_retries=3,
        http_client=mock_client,
    )

    event = WebhookEvent.create(
        event_type=WebhookEventType.ANALYSIS_FAILED,
        analysis_id=analysis.id,
        tenant_id="ens",
        payload={"error": "Dados insuficientes"},
    )

    # Tentativa 1 -> FAILED
    d1 = await dispatcher.dispatch(event, "https://ens.edu.br/fail")
    assert d1.status == WebhookDeliveryStatus.FAILED.value
    assert d1.attempt_count == 1

    # Tentativa 2 -> FAILED
    d2 = await dispatcher.dispatch(event, "https://ens.edu.br/fail")
    assert d2.status == WebhookDeliveryStatus.FAILED.value
    assert d2.attempt_count == 2

    # Tentativa 3 (atinge limite de 3) -> DEAD_LETTER
    d3 = await dispatcher.dispatch(event, "https://ens.edu.br/fail")
    assert d3.status == WebhookDeliveryStatus.DEAD_LETTER.value
    assert d3.attempt_count == 3
