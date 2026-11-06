import json
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.analysis_webhooks import deliver_pending_webhooks
from prometeus.application.create_analysis import CreateAnalysisCommand, CreateAnalysisUseCase
from prometeus.domain.analyses import AnalysisRecommendation
from prometeus.domain.configuration import AppSettings
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base, WebhookDeliveryModel
from prometeus.infrastructure.webhooks.dispatcher import WebhookDispatcher


async def test_completion_persists_webhook_and_retry_delivers_once(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "isolated-test-webhook-secret")
    monkeypatch.setenv("WEBHOOK_TARGET_URL", "https://institution.example/hook")
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        result = await CreateAnalysisUseCase(session).execute(
            CreateAnalysisCommand("ens", "Hook fixture", {}, "webhook-runtime", "test")
        )
        await session.commit()
        repo = AnalysisRepository(session)
        analysis = await repo.get_by_id(result.analysis_id)
        analysis.start("test")
        await repo.save(analysis)
        analysis.complete(AnalysisRecommendation.INSUFFICIENT_EVIDENCE, "test")
        await repo.save(analysis)
        await session.commit()
        delivery = (await session.execute(select(WebhookDeliveryModel))).scalar_one()
        assert delivery.status == "PENDING"
        calls = []

        def handler(request):
            calls.append(json.loads(request.content))
            assert "X-Prometeus-Signature" in request.headers
            return httpx.Response(503 if len(calls) == 1 else 200)

        settings = AppSettings()
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            sender = WebhookDispatcher(session, secret=settings.WEBHOOK_SECRET, http_client=client)
            assert await deliver_pending_webhooks(session, settings, sender) == 1
            assert delivery.status == "FAILED"
            assert await deliver_pending_webhooks(session, settings, sender) == 0
            delivery.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
            await session.commit()
            assert await deliver_pending_webhooks(session, settings, sender) == 1
            assert delivery.status == "DELIVERED"
            assert await deliver_pending_webhooks(session, settings, sender) == 0
        assert len(calls) == 2
        assert calls[0]["event_id"] == calls[1]["event_id"]
    await engine.dispose()
