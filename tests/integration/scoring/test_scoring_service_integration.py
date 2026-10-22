"""Testes de integração para ScoringService e ciclo de vida da Análise (ADR-0005)."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.application.scoring_service import ScoringService
from prometeus.domain.analyses import (
    Analysis,
    AnalysisRecommendation,
    AnalysisStatus,
)
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base, ScoringResultModel


@pytest.fixture
async def async_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_scoring_service_completes_analysis_with_recommendation(
    async_session: AsyncSession,
) -> None:
    repo = AnalysisRepository(async_session)
    analysis = Analysis.create(
        tenant_id="ens",
        course_name="MBA em Subscrição e Resseguros",
        correlation_id="corr-sc-1",
    )
    await repo.save(analysis)
    await async_session.commit()

    assert analysis.status == AnalysisStatus.QUEUED
    assert analysis.recommendation is None  # ADR-0005: nulo até COMPLETED

    service = ScoringService(session=async_session)

    pillar_inputs = {
        "internal_history": {
            "comparable_fit_score": 90.0,
            "conversion_rate": 0.15,
            "enrollments_count": 40,
        },
        "paid_competition": {"ad_count": 5, "competition_index": 0.70, "cpc_brl": 5.0},
        "search_and_media": {
            "monthly_volume": 3000,
            "growth_trend_pct": 20.0,
            "average_interest": 80.0,
        },
        "employability": {"open_jobs_count": 35, "salary_median_brl": 12000.0},
        "syllabus_fit": {"jev_syllabus_score": 95.0, "market_pain_points_covered_pct": 0.90},
        "pricing": {"proposed_price_brl": 15000.0, "market_median_price_brl": 15500.0},
    }

    result = await service.execute_scoring(
        pillar_inputs=pillar_inputs,
        analysis=analysis,
        profile_id="default-v1",
        correlation_id="corr-sc-1",
        is_experimental=False,
    )
    await async_session.commit()

    # ADR-0005: Análise deve estar COMPLETED com recommendation APPROVED
    assert analysis.status == AnalysisStatus.COMPLETED
    assert analysis.recommendation == AnalysisRecommendation.APPROVED
    assert result.recommendation == AnalysisRecommendation.APPROVED
    assert result.viability_score >= 75.0
    assert result.coverage_score == 1.0

    # Verifica persistência no banco
    stmt = select(ScoringResultModel).where(ScoringResultModel.analysis_id == analysis.id)
    row = (await async_session.execute(stmt)).scalar_one_or_none()
    assert row is not None
    assert row.viability_score == result.viability_score
    assert row.recommendation == "APPROVED"
    assert row.is_experimental is False
