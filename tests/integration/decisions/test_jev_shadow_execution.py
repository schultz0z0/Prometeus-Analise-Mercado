"""Testes de integração para execução em Shadow Mode e persistência de envelopes (Fase 6)."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.application.decision_service import DecisionService
from prometeus.application.shadow_decision_service import ShadowDecisionService
from prometeus.domain.analyses import Analysis
from prometeus.domain.ports.decision_model import (
    DecisionModelPort,
    DecisionPack,
    DecisionResult,
    ModelIdentity,
)
from prometeus.infrastructure.db.models import Base, DecisionResultModel


class StubPrimaryModel(DecisionModelPort):
    def model_identity(self) -> ModelIdentity:
        return ModelIdentity(provider="openai", model="gpt-4o-mini", mode="llm")

    def component_versions(self, pack_id: str, context: dict[str, Any]) -> dict[str, str]:
        return {"adapter": "1.0"}

    async def execute_choice(
        self, pack: DecisionPack, context: dict[str, Any], evidence_ids: list[str] | None = None
    ) -> DecisionResult:
        return DecisionResult.choice(
            pack_id=pack.pack_id,
            selected="OBSERVED",
            confidence=0.91,
            evidence_ids=evidence_ids,
        )

    async def execute_score(
        self, pack: DecisionPack, context: dict[str, Any], evidence_ids: list[str] | None = None
    ) -> DecisionResult:
        return DecisionResult.score(
            pack_id=pack.pack_id,
            value=78.0,
            confidence=0.88,
            evidence_ids=evidence_ids,
        )


class StubShadowModel(DecisionModelPort):
    def model_identity(self) -> ModelIdentity:
        return ModelIdentity(provider="typesafe_jev", model="jev-2026.1", mode="jev")

    def component_versions(self, pack_id: str, context: dict[str, Any]) -> dict[str, str]:
        return {"client": "jev-1.0"}

    async def execute_choice(
        self, pack: DecisionPack, context: dict[str, Any], evidence_ids: list[str] | None = None
    ) -> DecisionResult:
        return DecisionResult.choice(
            pack_id=pack.pack_id,
            selected="OBSERVED",
            confidence=0.89,
            evidence_ids=evidence_ids,
        )

    async def execute_score(
        self, pack: DecisionPack, context: dict[str, Any], evidence_ids: list[str] | None = None
    ) -> DecisionResult:
        return DecisionResult.score(
            pack_id=pack.pack_id,
            value=82.0,
            confidence=0.85,
            evidence_ids=evidence_ids,
        )


@pytest.fixture
async def async_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session
    await engine.dispose()


class TestJEVShadowIntegration:
    @pytest.mark.asyncio
    async def test_shadow_execution_persists_production_decision_and_shadow_telemetry(
        self, async_db: AsyncSession, tmp_path: Any
    ) -> None:
        packs_dir = tmp_path / "packs"
        packs_dir.mkdir()
        pack_file = packs_dir / "evidence-support-v1.yaml"
        pack_file.write_text(
            """
pack_id: evidence-support-v1
version: "1.0.0"
decision_type: CHOICE
question: "A evidência suporta a claim?"
options: ["OBSERVED", "SUGGESTIVE", "UNSUPPORTED"]
rubric: {}
notes: []
""",
            encoding="utf-8",
        )

        primary_service = DecisionService(
            decision_model=StubPrimaryModel(),
            session=async_db,
            packs_dir=packs_dir,
        )
        shadow_service = ShadowDecisionService(
            primary_service=primary_service,
            shadow_model=StubShadowModel(),
            enabled=True,
        )

        analysis = Analysis.create(
            analysis_id="test-analysis-shadow-01",
            course_name="MBA em Gestão de Riscos",
            tenant_id="ens",
            correlation_id="corr-shadow-01",
        )

        # Executa julgamento via shadow service
        res = await shadow_service.execute_judgment(
            pack_id="evidence-support-v1",
            context={"claim": "A carga horária é de 360h"},
            analysis=analysis,
            evidence_ids=["ev-fgv-01"],
        )

        assert res.selected_choice == "OBSERVED"
        assert res.confidence == 0.91

        # Verifica persistência relacional: a decisão oficial gravada é da produção
        stmt_dec = select(DecisionResultModel).where(
            DecisionResultModel.analysis_id == "test-analysis-shadow-01"
        )
        stored_dec = (await async_db.execute(stmt_dec)).scalar_one_or_none()
        assert stored_dec is not None
        assert stored_dec.selected_choice == "OBSERVED"
        assert stored_dec.confidence == 0.91

        # Verifica envelopes de auditoria registrados
        assert len(primary_service.envelopes) >= 1
        assert len(shadow_service.comparison_records) == 1
        comp = shadow_service.comparison_records[0]
        assert comp.is_concordant is True
        assert comp.primary_model == "gpt-4o-mini"
        assert comp.shadow_model == "jev-2026.1"
