"""Testes operacionais de simulação de falhas externas e resiliência (JEV, Apify, CRM, Webhook)."""

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.domain.analyses import Analysis, AnalysisStatus
from prometeus.domain.webhooks import (
    WebhookDeliveryStatus,
    WebhookEvent,
    WebhookEventType,
)
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base
from prometeus.infrastructure.webhooks.dispatcher import WebhookDispatcher


@pytest.fixture
async def fail_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_webhook_dead_letter_after_consecutive_failures(fail_session: AsyncSession) -> None:
    target_url = "https://external.ens.edu.br/webhook/failure"
    mock_transport = httpx.MockTransport(
        lambda request: httpx.Response(500, text="Internal Server Error")
    )
    mock_client = httpx.AsyncClient(transport=mock_transport)

    event = WebhookEvent.create(
        event_type=WebhookEventType.ANALYSIS_FAILED,
        analysis_id="an-fail-001",
        tenant_id="ens",
        payload={"error": "Connector timeout"},
    )

    dispatcher = WebhookDispatcher(
        db_session=fail_session,
        max_retries=3,
        shadow_mode=False,
        http_client=mock_client,
    )

    # Tentativa 1: FAILED
    d1 = await dispatcher.dispatch(event, target_url)
    assert d1.status == WebhookDeliveryStatus.FAILED.value
    assert d1.attempt_count == 1

    # Tentativa 2: FAILED
    d2 = await dispatcher.dispatch(event, target_url)
    assert d2.status == WebhookDeliveryStatus.FAILED.value
    assert d2.attempt_count == 2

    # Tentativa 3 (atinge limite max_retries=3): DEAD_LETTER
    d3 = await dispatcher.dispatch(event, target_url)
    assert d3.status == WebhookDeliveryStatus.DEAD_LETTER.value
    assert d3.attempt_count == 3
    assert "HTTP 500" in (d3.last_error or "")


@pytest.mark.asyncio
async def test_analysis_resilience_transition_to_blocked_on_unrecoverable_failure(
    fail_session: AsyncSession,
) -> None:
    repo = AnalysisRepository(fail_session)
    analysis = Analysis.create(
        tenant_id="ens",
        course_name="MBA em Regulação de Resseguros",
        correlation_id="corr-resilience-1",
    )
    analysis.start(correlation_id="corr-resilience-1")
    await repo.save(analysis)
    await fail_session.commit()

    # Simula indisponibilidade crítica de integridade externa
    analysis.block(
        correlation_id="corr-resilience-1",
        reason="JEV_SERVICE_UNAVAILABLE: Circuit breaker aberto após 3 falhas de timeout consecutivas.",
    )
    await repo.save(analysis)
    await fail_session.commit()

    reloaded = await repo.get_by_id(analysis.id)
    assert reloaded is not None
    assert reloaded.status == AnalysisStatus.BLOCKED
    assert reloaded.audit_events[-1].reason is not None
    assert "Circuit breaker aberto" in reloaded.audit_events[-1].reason
