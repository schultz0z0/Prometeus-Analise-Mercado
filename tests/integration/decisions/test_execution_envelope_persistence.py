"""Envelope de execução persistido por tentativa no DecisionService (tarefa 0.3)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.application.decision_service import DecisionService
from prometeus.domain.analyses import Analysis
from prometeus.domain.execution_envelope import (
    MeasuredCost,
    ProviderCallTelemetry,
    TokenUsage,
    record_provider_call,
)
from prometeus.domain.ports.decision_model import DecisionPack, DecisionResult, ModelIdentity
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base, ExecutionEnvelopeModel
from prometeus.infrastructure.jev.client import JEVError, JEVServiceUnavailableError
from prometeus.infrastructure.jev.fake_client import FakeDecisionClient


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as db:
        yield db
    await engine.dispose()


async def _analysis(db: AsyncSession) -> Analysis:
    analysis = Analysis.create(tenant_id="ens", course_name="MBA Seguros", correlation_id="c")
    analysis.start("c")
    await AnalysisRepository(db).save(analysis)
    await db.commit()
    return analysis


async def _envelopes(db: AsyncSession, analysis_id: str) -> list[ExecutionEnvelopeModel]:
    rows = await db.execute(
        select(ExecutionEnvelopeModel)
        .where(ExecutionEnvelopeModel.analysis_id == analysis_id)
        .order_by(ExecutionEnvelopeModel.started_at)
    )
    return list(rows.scalars().all())


class TelemetryClient(FakeDecisionClient):
    """Fake que registra telemetria como um provedor real faria."""

    async def execute_choice(
        self, pack: DecisionPack, context: dict[str, Any], evidence_ids: list[str] | None = None
    ) -> DecisionResult:
        record_provider_call(
            ProviderCallTelemetry(
                provider="openai_chat_completions",
                model="gpt-effective-2026",
                attempts=1,
                usage=TokenUsage(input_tokens=120, output_tokens=8, total_tokens=128),
                cost=MeasuredCost.unavailable("provider_did_not_return_cost"),
            )
        )
        return await super().execute_choice(pack, context, evidence_ids)


class InvalidResponseClient(FakeDecisionClient):
    async def execute_choice(
        self, pack: DecisionPack, context: dict[str, Any], evidence_ids: list[str] | None = None
    ) -> DecisionResult:
        raise ValueError("A LLM retornou a opção não permitida 'MAYBE'.")


async def test_successful_judgment_persists_envelope_linked_to_decision(
    session: AsyncSession,
) -> None:
    analysis = await _analysis(session)
    service = DecisionService(TelemetryClient(canned_choices={"readiness-v1": "READY"}), session)
    result = await service.execute_judgment(
        pack_id="readiness-v1",
        context={"course_name": "MBA Seguros"},
        analysis=analysis,
        correlation_id="c",
        evidence_ids=["ev-1"],
        component_versions={"projector": "p-v1"},
    )
    await session.commit()

    [row] = await _envelopes(session, analysis.id)
    assert row.tenant_id == "ens"
    assert row.stage == "readiness-v1"
    assert row.operation == "readiness-v1"
    assert row.attempt == 1
    assert row.outcome == "SUCCEEDED"
    assert row.decision_id == result.id
    assert row.source_ids == ["ev-1"]
    assert row.model == "gpt-effective-2026"
    assert row.configured_model == "jev-fake-v1"
    assert row.mode == "fake"
    assert row.usage == {"input_tokens": 120, "output_tokens": 8, "total_tokens": 128}
    assert row.cost_status == "UNAVAILABLE"
    assert row.cost_usd is None
    assert row.component_versions["projector"] == "p-v1"
    assert row.component_versions["pack"].startswith("readiness-v1@")
    assert len(row.input_hash) == 64 and len(row.cache_key) == 64
    assert row.duration_ms is not None and row.duration_ms >= 0
    assert service.envelopes[-1].id == row.id


async def test_rejected_response_remains_auditable_and_counts_attempts(
    session: AsyncSession,
) -> None:
    analysis = await _analysis(session)
    service = DecisionService(InvalidResponseClient(), session)
    for _ in range(2):
        with pytest.raises(JEVError):
            await service.execute_judgment(
                pack_id="readiness-v1", context={"x": 1}, analysis=analysis, correlation_id="c"
            )
    await session.commit()

    rows = await _envelopes(session, analysis.id)
    assert [r.outcome for r in rows] == ["REJECTED", "REJECTED"]
    assert [r.attempt for r in rows] == [1, 2]
    assert rows[0].cache_key == rows[1].cache_key
    assert rows[0].decision_id is None
    assert rows[0].error_code == "ValueError"
    assert rows[0].usage is None
    assert rows[0].cost_usd is None and rows[0].cost_status == "UNAVAILABLE"


async def test_unavailable_provider_records_envelope_before_blocking(
    session: AsyncSession,
) -> None:
    analysis = await _analysis(session)
    service = DecisionService(FakeDecisionClient(simulate_unavailable=True), session)
    with pytest.raises(JEVServiceUnavailableError):
        await service.execute_judgment(
            pack_id="readiness-v1", context={}, analysis=analysis, correlation_id="c"
        )
    [row] = await _envelopes(session, analysis.id)
    assert row.outcome == "UNAVAILABLE"
    assert row.error_code == "ConnectionError"


async def test_envelope_snapshot_never_contains_secrets(session: AsyncSession) -> None:
    analysis = await _analysis(session)

    class Leaky(FakeDecisionClient):
        async def execute_choice(
            self,
            pack: DecisionPack,
            context: dict[str, Any],
            evidence_ids: list[str] | None = None,
        ) -> DecisionResult:
            raise RuntimeError("HTTP 401 Authorization: Bearer sk-LEAKED0123456789")

    service = DecisionService(Leaky(), session)
    with pytest.raises(JEVError):
        await service.execute_judgment(
            pack_id="readiness-v1",
            context={},
            analysis=analysis,
            correlation_id="c",
            component_versions={"api_key": "sk-LEAKED0123456789"},
        )
    [row] = await _envelopes(session, analysis.id)
    stored = json.dumps(
        {
            "detail": row.error_detail,
            "versions": row.component_versions,
            "snapshot": service.envelopes[-1].to_snapshot(),
        }
    )
    assert "LEAKED" not in stored
    assert row.outcome == "FAILED"


async def test_cache_key_depends_on_effective_identity_and_versions() -> None:
    client = FakeDecisionClient()
    service = DecisionService(client)
    base = service.cache_key_for("readiness-v1", {"x": 1}, component_versions={"p": "1"})
    assert base == service.cache_key_for("readiness-v1", {"x": 1}, component_versions={"p": "1"})
    assert base != service.cache_key_for("readiness-v1", {"x": 1}, component_versions={"p": "2"})
    client.model = "jev-fake-v2"
    assert base != service.cache_key_for(
        "readiness-v1", {"x": 1}, component_versions={"p": "1"}
    )
    assert client.model_identity() == ModelIdentity(
        provider="FakeDecisionClient", model="jev-fake-v2", mode="fake"
    )

