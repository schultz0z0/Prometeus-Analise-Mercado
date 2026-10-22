"""Testes de integração para persistência e integridade relacional de DossierModel no PostgreSQL."""

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
    DossierModel,
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


def test_dossiers_table_postgresql_compilation() -> None:
    """Valida se a tabela dossiers compila perfeitamente para o dialeto PostgreSQL (JSONB, UNIQUE, etc.)."""
    sql = str(CreateTable(DossierModel.__table__).compile(dialect=postgresql.dialect()))
    assert "CREATE TABLE dossiers" in sql
    assert "JSONB" in sql
    assert "analysis_id VARCHAR(64) NOT NULL" in sql
    assert "UNIQUE (analysis_id)" in sql
    assert "FOREIGN KEY(analysis_id) REFERENCES analyses (id) ON DELETE CASCADE" in sql


@pytest.mark.asyncio
async def test_dossier_lifecycle_and_cascade_delete(db_session: AsyncSession) -> None:
    repo = AnalysisRepository(db_session)
    analysis = Analysis.create(
        tenant_id="ens",
        course_name="MBA em Gestão de Sinistros e Riscos",
        correlation_id="corr-dossier-cascade",
    )
    await repo.save(analysis)
    await db_session.commit()

    dossier = DossierModel(
        id=str(uuid.uuid4()),
        analysis_id=analysis.id,
        prompt_version="dossier-v1",
        model_name="gpt-4o-mini",
        facts_hash="hash-123456",
        status="VERIFIED",
        executive_summary="Resumo executivo da análise de sinistros.",
        sections=[{"section_id": "sec_01", "title": "Diretoria", "content": "Texto executivo"}],
        claims=[{"claim_id": "CLM-01", "statement": "Claim test"}],
        cost_usd=0.005,
        created_at=datetime.now(UTC),
    )
    db_session.add(dossier)
    await db_session.commit()

    # Consulta vinculada
    stmt = select(DossierModel).where(DossierModel.analysis_id == analysis.id)
    retrieved = (await db_session.execute(stmt)).scalar_one_or_none()
    assert retrieved is not None
    assert retrieved.prompt_version == "dossier-v1"
    assert retrieved.executive_summary == "Resumo executivo da análise de sinistros."

    # Deleta a análise raiz e valida cascade delete
    db_analysis = (
        await db_session.execute(select(AnalysisModel).where(AnalysisModel.id == analysis.id))
    ).scalar_one()
    await db_session.delete(db_analysis)
    await db_session.commit()

    remaining = (await db_session.execute(stmt)).scalar_one_or_none()
    assert remaining is None
