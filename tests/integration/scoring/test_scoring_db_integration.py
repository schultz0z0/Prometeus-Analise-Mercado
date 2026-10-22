"""Testes de integração para persistência e integridade relacional de ScoringResultModel no PostgreSQL."""

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
    ScoringResultModel,
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


def test_scoring_results_table_postgresql_compilation() -> None:
    """Valida se a tabela scoring_results compila perfeitamente para o dialeto PostgreSQL (JSONB, UNIQUE, etc.)."""
    sql = str(CreateTable(ScoringResultModel.__table__).compile(dialect=postgresql.dialect()))
    assert "CREATE TABLE scoring_results" in sql
    assert "JSONB" in sql
    assert "analysis_id VARCHAR(64) NOT NULL" in sql
    assert "UNIQUE (analysis_id)" in sql
    assert "FOREIGN KEY(analysis_id) REFERENCES analyses (id) ON DELETE CASCADE" in sql


@pytest.mark.asyncio
async def test_scoring_result_lifecycle_and_cascade_delete(db_session: AsyncSession) -> None:
    repo = AnalysisRepository(db_session)
    analysis = Analysis.create(
        tenant_id="ens",
        course_name="MBA em Sinistros",
        correlation_id="corr-sc-cascade",
    )
    await repo.save(analysis)
    await db_session.commit()

    scoring_model = ScoringResultModel(
        id=str(uuid.uuid4()),
        analysis_id=analysis.id,
        profile_id="default-v1",
        viability_score=84.5,
        coverage_score=1.0,
        confidence_score=0.92,
        partial_score=84.5,
        recommendation="APPROVED",
        is_experimental=False,
        pillar_scores={"internal_history": {"score": 85.0}},
        gate_details={"passed_gates": True},
        created_at=datetime.now(UTC),
    )
    db_session.add(scoring_model)
    await db_session.commit()

    # Consulta vinculada
    stmt = select(ScoringResultModel).where(ScoringResultModel.analysis_id == analysis.id)
    retrieved = (await db_session.execute(stmt)).scalar_one_or_none()
    assert retrieved is not None
    assert retrieved.viability_score == 84.5

    # Deleta análise raiz e verifica cascade delete
    db_analysis = (
        await db_session.execute(select(AnalysisModel).where(AnalysisModel.id == analysis.id))
    ).scalar_one()
    await db_session.delete(db_analysis)
    await db_session.commit()

    # Confirma que scoring_result foi removido em cascade
    remaining = (await db_session.execute(stmt)).scalar_one_or_none()
    assert remaining is None
