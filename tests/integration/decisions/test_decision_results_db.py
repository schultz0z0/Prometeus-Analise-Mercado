"""Testes de integração para persistência e integridade relacional de DecisionResultModel no banco."""

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
    DecisionResultModel,
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


def test_decision_results_table_postgresql_compilation() -> None:
    """Valida se a tabela decision_results compila perfeitamente para o dialeto PostgreSQL (JSONB, Boolean, etc.)."""
    table = DecisionResultModel.__table__
    sql = str(CreateTable(table).compile(dialect=postgresql.dialect()))

    assert "CREATE TABLE decision_results" in sql
    assert "JSONB" in sql  # Garante uso de JSONB no PostgreSQL
    assert "analysis_id VARCHAR(64) NOT NULL" in sql
    assert "requires_human_review BOOLEAN NOT NULL" in sql
    assert "FOREIGN KEY(analysis_id) REFERENCES analyses (id) ON DELETE CASCADE" in sql


@pytest.mark.asyncio
async def test_decision_result_lifecycle_and_cascade_delete(db_session: AsyncSession) -> None:
    repo = AnalysisRepository(db_session)
    analysis = Analysis.create(
        tenant_id="ens",
        course_name="MBA em Solvência e Riscos",
        correlation_id="corr-cascade",
    )
    await repo.save(analysis)
    await db_session.commit()

    # Adiciona 2 decisões
    dec1 = DecisionResultModel(
        id=str(uuid.uuid4()),
        analysis_id=analysis.id,
        pack_id="readiness-v1",
        decision_type="CHOICE",
        confidence=0.92,
        is_noul=False,
        selected_choice="READY",
        distribution={"READY": 0.92, "NEEDS_CLARIFICATION": 0.08},
        score_value=None,
        requires_human_review=False,
        evidence_ids=["ev-1"],
        model_version="jev-2026.1-pinned",
        created_at=datetime.now(UTC),
    )
    dec2 = DecisionResultModel(
        id=str(uuid.uuid4()),
        analysis_id=analysis.id,
        pack_id="syllabus-fit-v1",
        decision_type="SCORE",
        confidence=0.88,
        is_noul=False,
        selected_choice=None,
        distribution={},
        score_value=85.0,
        requires_human_review=False,
        evidence_ids=["ev-syllabus"],
        model_version="jev-2026.1-pinned",
        created_at=datetime.now(UTC),
    )
    db_session.add_all([dec1, dec2])
    await db_session.commit()

    # Consulta vinculada
    stmt = (
        select(DecisionResultModel)
        .where(DecisionResultModel.analysis_id == analysis.id)
        .order_by(DecisionResultModel.created_at)
    )
    results = (await db_session.execute(stmt)).scalars().all()
    assert len(results) == 2
    assert results[0].pack_id == "readiness-v1"
    assert results[1].pack_id == "syllabus-fit-v1"

    # Deleta análise via modelo SQLAlchemy para verificar cascade
    db_analysis = (
        await db_session.execute(select(AnalysisModel).where(AnalysisModel.id == analysis.id))
    ).scalar_one()
    await db_session.delete(db_analysis)
    await db_session.commit()

    # Verifica se os registros filhos foram removidos em cascade
    remaining = (await db_session.execute(stmt)).scalars().all()
    assert len(remaining) == 0
