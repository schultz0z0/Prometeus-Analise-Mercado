"""Reuso da qualificação somente com mesmo input efetivo, versões e modelo (tarefa 0.3)."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.application import qualify_market_evidence as qualification
from prometeus.application.decision_service import DecisionService
from prometeus.domain.analyses import Analysis
from prometeus.domain.research import CourseUnderstanding
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base, MarketEvidenceModel
from prometeus.infrastructure.jev.fake_client import FakeDecisionClient


async def test_model_or_projector_change_requalifies_while_identical_run_reuses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as db:
        analysis = Analysis.create(tenant_id="ens", course_name="MBA Seguros", correlation_id="q")
        await AnalysisRepository(db).save(analysis)
        payload = {"title": "Analista de sinistros", "location": "São Paulo, Brazil"}
        db.add(
            MarketEvidenceModel(
                id="job",
                analysis_id=analysis.id,
                evidence_type="JOB_MARKET",
                source_name="test",
                source_url="https://example.com/job",
                collector="test",
                content_hash="job",
                title="job",
                raw_payload=payload,
                sanitized_data=payload,
                quality_score=1,
                cost_usd=0,
            )
        )
        await db.commit()
        model = FakeDecisionClient(canned_choices={"market-relevance-v1": "CONTEXT"})
        service = qualification.EvidenceQualificationService(db, DecisionService(model, db))
        understanding = CourseUnderstanding(analysis_id=analysis.id, course_title="MBA Seguros")
        row = await db.get(MarketEvidenceModel, "job")
        assert row is not None

        await service.qualify(analysis, understanding, "q")
        first = row.sanitized_data["_qualification"]
        assert len(first["execution_cache_key"]) == 64
        assert first["component_versions"]["projector"] == qualification.PROJECTOR_VERSION

        await service.qualify(analysis, understanding, "q")
        assert row.sanitized_data["_qualification"]["decision_id"] == first["decision_id"]

        model.model = "jev-fake-v2"
        await service.qualify(analysis, understanding, "q")
        second = row.sanitized_data["_qualification"]
        assert second["decision_id"] != first["decision_id"]
        assert second["execution_cache_key"] != first["execution_cache_key"]

        monkeypatch.setattr(qualification, "PROJECTOR_VERSION", "typed-projection-v3")
        await service.qualify(analysis, understanding, "q")
        third = row.sanitized_data["_qualification"]
        assert third["decision_id"] != second["decision_id"]

        # Qualificações legadas sem chave de execução não são reaproveitadas como replay exato.
        legacy = dict(row.sanitized_data)
        legacy["_qualification"] = {
            k: v for k, v in third.items() if k != "execution_cache_key"
        }
        row.sanitized_data = legacy
        await db.commit()
        await service.qualify(analysis, understanding, "q")
        assert row.sanitized_data["_qualification"]["decision_id"] != third["decision_id"]
    await engine.dispose()

