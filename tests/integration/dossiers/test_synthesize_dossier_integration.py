"""Testes de integração para DossierSynthesisService e fluxo ponta a ponta de síntese de dossiê."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.application.synthesize_dossier import DossierSynthesisService
from prometeus.domain.analyses import Analysis
from prometeus.domain.dossiers import DossierStatus
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import (
    Base,
    DecisionResultModel,
    DossierModel,
    MarketEvidenceModel,
    ScoringResultModel,
)
from prometeus.infrastructure.llm.fake import FakeGenerativeModel


@pytest.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_synthesize_and_verify_e2e_flow(db_session: AsyncSession) -> None:
    repo = AnalysisRepository(db_session)
    analysis = Analysis.create(
        tenant_id="ens",
        course_name="MBA em Inteligência de Dados para Subscrição de Seguros",
        correlation_id="corr-dossier-e2e",
    )
    await repo.save(analysis)
    await db_session.commit()

    # 1. Cria ScoringResult vinculado
    scoring = ScoringResultModel(
        id=str(uuid.uuid4()),
        analysis_id=analysis.id,
        profile_id="default-v1",
        viability_score=88.5,
        coverage_score=1.0,
        confidence_score=0.91,
        partial_score=88.5,
        recommendation="APPROVED",
        is_experimental=False,
        pillar_scores={
            "internal_history": {"raw_score": 90.0, "is_present": True},
            "search_and_media": {"raw_score": 85.0, "is_present": True},
        },
        gate_details={"all_passed": True},
        created_at=datetime.now(UTC),
    )
    db_session.add(scoring)

    # 2. Cria MarketEvidence vinculada
    ev = MarketEvidenceModel(
        id=str(uuid.uuid4()),
        analysis_id=analysis.id,
        evidence_type="SEARCH_VOLUME",
        source_name="GoogleAds",
        source_url="https://ads.google.com",
        collector="google_ads_collector",
        content_hash="hash-ev-ads",
        title="Buscas para Subscrição de Riscos",
        raw_payload={},
        sanitized_data={"monthly_volume": 4500, "cpc_brl": 6.8},
        quality_score=0.95,
        cost_usd=0.01,
        collected_at=datetime.now(UTC),
    )
    db_session.add(ev)

    # 3. Cria DecisionResult do JEV
    dec = DecisionResultModel(
        id=str(uuid.uuid4()),
        analysis_id=analysis.id,
        pack_id="syllabus-fit-v1",
        decision_type="score",
        confidence=0.92,
        is_noul=False,
        selected_choice=None,
        distribution={},
        score_value=92.0,
        requires_human_review=False,
        evidence_ids=[],
        model_version="jev-gpt4o-2026-03",
        created_at=datetime.now(UTC),
    )
    db_session.add(dec)
    await db_session.commit()

    # 4. Executa síntese do dossiê
    fake_llm = FakeGenerativeModel()
    service = DossierSynthesisService(db_session, fake_llm)

    dossier_output = await service.synthesize_and_verify(analysis.id, prompt_version="dossier-v1")

    assert dossier_output is not None
    assert dossier_output.status == DossierStatus.VERIFIED
    assert len(dossier_output.sections) == 3
    assert len(dossier_output.claims) >= 2

    # Verifica persistência no PostgreSQL / SQLite
    stmt = select(DossierModel).where(DossierModel.analysis_id == analysis.id)
    persisted = (await db_session.execute(stmt)).scalar_one_or_none()
    assert persisted is not None
    assert persisted.status == "VERIFIED"
    assert persisted.prompt_version == "dossier-v1"
    assert "MBA em Inteligência de Dados" in persisted.executive_summary
    assert len(persisted.sections) == 3
