"""Testes de integração para persistência e integridade relacional de ResearchPlanModel e MarketEvidenceModel."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateTable

from prometeus.domain.analyses import Analysis
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import (
    AnalysisModel,
    Base,
    MarketEvidenceModel,
    ResearchPlanModel,
)


@pytest.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


def test_market_evidence_tables_postgresql_compilation() -> None:
    """Valida se as tabelas research_plans e market_evidences compilam perfeitamente para o dialeto PostgreSQL (JSONB)."""
    plan_sql = str(CreateTable(ResearchPlanModel.__table__).compile(dialect=postgresql.dialect()))
    assert "CREATE TABLE research_plans" in plan_sql
    assert "JSONB" in plan_sql
    assert "FOREIGN KEY(analysis_id) REFERENCES analyses (id) ON DELETE CASCADE" in plan_sql

    ev_sql = str(CreateTable(MarketEvidenceModel.__table__).compile(dialect=postgresql.dialect()))
    assert "CREATE TABLE market_evidences" in ev_sql
    assert "JSONB" in ev_sql
    assert "FOREIGN KEY(analysis_id) REFERENCES analyses (id) ON DELETE CASCADE" in ev_sql


@pytest.mark.asyncio
async def test_research_plan_and_evidence_cascade_delete(db_session: AsyncSession) -> None:
    repo = AnalysisRepository(db_session)
    analysis = Analysis.create(
        tenant_id="ens",
        course_name="MBA em Riscos",
        correlation_id="corr-cascade-ev",
    )
    await repo.save(analysis)
    await db_session.commit()

    # Adiciona ResearchPlan
    plan = ResearchPlanModel(
        id=str(uuid.uuid4()),
        analysis_id=analysis.id,
        tenant_id="ens",
        cache_key="ens:seguros:key-1",
        enabled_sources=["google_trends", "google_ads"],
        budget_limit_usd=2.00,
        spent_usd=0.00,
        allocated_budget={"google_trends": 0.0, "google_ads": 0.0},
        status="PLANNED",
    )

    # Adiciona MarketEvidence
    evidence = MarketEvidenceModel(
        id=str(uuid.uuid4()),
        analysis_id=analysis.id,
        evidence_type="TRENDS",
        source_name="google_trends",
        source_url="http://trends.com",
        collector="google_trends_collector",
        content_hash="abc123hash",
        title="Interesse de busca",
        raw_payload={"term": "mba seguros", "interest": 75},
        sanitized_data={"term": "mba seguros", "interest": 75},
        quality_score=1.0,
        cost_usd=0.0,
        collected_at=datetime.now(UTC),
    )

    db_session.add_all([plan, evidence])
    await db_session.commit()

    # Verifica persistência
    plans = (
        (
            await db_session.execute(
                select(ResearchPlanModel).where(ResearchPlanModel.analysis_id == analysis.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(plans) == 1

    evidences = (
        (
            await db_session.execute(
                select(MarketEvidenceModel).where(MarketEvidenceModel.analysis_id == analysis.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(evidences) == 1
    assert evidences[0].evidence_type == "TRENDS"

    # Deleta a Análise raiz e verifica exclusão em cascata
    db_analysis = (
        await db_session.execute(select(AnalysisModel).where(AnalysisModel.id == analysis.id))
    ).scalar_one()
    await db_session.delete(db_analysis)
    await db_session.commit()

    # Verifica se os registros filhos foram removidos
    plans_after = (
        (
            await db_session.execute(
                select(ResearchPlanModel).where(ResearchPlanModel.analysis_id == analysis.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(plans_after) == 0

    evidences_after = (
        (
            await db_session.execute(
                select(MarketEvidenceModel).where(MarketEvidenceModel.analysis_id == analysis.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(evidences_after) == 0
