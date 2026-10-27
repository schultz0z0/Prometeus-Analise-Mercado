import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.application.synthesize_dossier import (
    DossierSynthesisService,
    DossierVerificationError,
)
from prometeus.domain.analyses import Analysis
from prometeus.domain.dossiers import (
    ClaimType,
    DossierClaim,
    DossierOutput,
    DossierSection,
    DossierStatus,
)
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base, DossierModel, ScoringResultModel
from prometeus.infrastructure.llm.fake import FakeGenerativeModel


@pytest.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session
    await engine.dispose()


async def seed_scored_analysis(session: AsyncSession) -> Analysis:
    analysis = Analysis.create(
        tenant_id="ens",
        course_name="Curso inédito auditável",
        correlation_id="corr-no-fallback",
    )
    await AnalysisRepository(session).save(analysis)
    session.add(
        ScoringResultModel(
            id=str(uuid.uuid4()),
            analysis_id=analysis.id,
            profile_id="default-v1",
            viability_score=72.0,
            coverage_score=0.9,
            confidence_score=0.8,
            partial_score=80.0,
            recommendation="APPROVED_WITH_ADJUSTMENTS",
            is_experimental=True,
            pillar_scores={"internal_history": {"raw_score": 72.0, "is_present": True}},
            gate_details={},
            created_at=datetime.now(UTC),
        )
    )
    await session.commit()
    return analysis


@pytest.mark.asyncio
async def test_llm_failure_propagates_and_does_not_persist_a_fallback(
    db_session: AsyncSession,
) -> None:
    analysis = await seed_scored_analysis(db_session)
    service = DossierSynthesisService(
        db_session,
        FakeGenerativeModel(simulate_error=True),
    )

    with pytest.raises(ConnectionError, match="Falha simulada"):
        await service.synthesize_and_verify(analysis.id)

    persisted = (
        await db_session.execute(
            select(DossierModel).where(DossierModel.analysis_id == analysis.id)
        )
    ).scalar_one_or_none()
    assert persisted is None


@pytest.mark.asyncio
async def test_untraceable_claim_blocks_persistence_instead_of_publishing_dossier(
    db_session: AsyncSession,
) -> None:
    analysis = await seed_scored_analysis(db_session)
    invalid = DossierOutput(
        analysis_id=analysis.id,
        model_name="test-model",
        executive_summary="Resumo sem suporte.",
        sections=[
            DossierSection(
                section_id="executive",
                title="Executivo",
                target_audience="executive",
                content="Há grande oportunidade.",
                claim_ids=["CLM-1"],
            )
        ],
        claims=[
            DossierClaim(
                claim_id="CLM-1",
                statement="Há grande oportunidade.",
                claim_type=ClaimType.QUALITATIVE,
                evidence_ids=[],
            )
        ],
        facts_hash="will-be-replaced-by-test-client",
        status=DossierStatus.DRAFT,
    )
    service = DossierSynthesisService(
        db_session,
        FakeGenerativeModel(canned_dossier=invalid),
    )
    facts = await service.build_facts(analysis.id)
    invalid.facts_hash = facts.compute_facts_hash()

    with pytest.raises(DossierVerificationError, match="não passou"):
        await service.synthesize_and_verify(analysis.id)

    persisted = (
        await db_session.execute(
            select(DossierModel).where(DossierModel.analysis_id == analysis.id)
        )
    ).scalar_one_or_none()
    assert persisted is None
