import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.domain.analyses import (
    Analysis,
    AnalysisRecommendation,
    AnalysisStatus,
    AnalysisStep,
)
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base


@pytest.fixture
async def async_session() -> AsyncSession:
    # Cria engine de teste assíncrona
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


async def test_save_and_retrieve_analysis(async_session: AsyncSession) -> None:
    repo = AnalysisRepository(async_session)

    analysis = Analysis.create(
        tenant_id="ens",
        course_name="Especialização em Subscrição de Riscos",
        correlation_id="corr-init-1",
        proposal_data={"target_audience": "Executivos de seguros", "price": 12000},
    )

    await repo.save(analysis)
    await async_session.commit()

    retrieved = await repo.get_by_id(analysis.id)
    assert retrieved is not None
    assert retrieved.id == analysis.id
    assert retrieved.tenant_id == "ens"
    assert retrieved.course_name == "Especialização em Subscrição de Riscos"
    assert retrieved.status == AnalysisStatus.QUEUED
    assert retrieved.recommendation is None
    assert len(retrieved.audit_events) == 1
    assert retrieved.audit_events[0].to_status == AnalysisStatus.QUEUED


async def test_update_status_and_audit_trail(async_session: AsyncSession) -> None:
    repo = AnalysisRepository(async_session)

    analysis = Analysis.create(
        tenant_id="ens",
        course_name="MBA em Inteligência de Sinistros",
        correlation_id="corr-1",
    )
    await repo.save(analysis)
    await async_session.commit()

    # Transiciona para RUNNING
    analysis.start(correlation_id="corr-2", reason="Worker reservou vaga")
    await repo.save(analysis)
    await async_session.commit()

    # Transiciona para COMPLETED
    analysis.complete(
        recommendation=AnalysisRecommendation.APPROVED,
        correlation_id="corr-3",
        reason="Score acima do limiar",
    )
    await repo.save(analysis)
    await async_session.commit()

    retrieved = await repo.get_by_id(analysis.id)
    assert retrieved is not None
    assert retrieved.status == AnalysisStatus.COMPLETED
    assert retrieved.recommendation == AnalysisRecommendation.APPROVED
    assert len(retrieved.audit_events) == 3
    assert retrieved.audit_events[0].to_status == AnalysisStatus.QUEUED
    assert retrieved.audit_events[1].to_status == AnalysisStatus.RUNNING
    assert retrieved.audit_events[2].to_status == AnalysisStatus.COMPLETED


async def test_save_steps_and_snapshots(async_session: AsyncSession) -> None:
    repo = AnalysisRepository(async_session)

    analysis = Analysis.create(
        tenant_id="ens",
        course_name="Curso Técnico em Perícia",
        correlation_id="corr-step-1",
    )
    step1 = AnalysisStep(
        id="step-1",
        analysis_id=analysis.id,
        step_number=1,
        name="intake_validation",
        status="COMPLETED",
        output_summary={"validated": True},
    )
    analysis.steps.append(step1)

    await repo.save(analysis)
    await repo.save_config_snapshot(
        analysis_id=analysis.id,
        tenant_id="ens",
        scoring_profile_id="default-v1",
        tenant_config_snapshot={"features": {"pricing": True}},
        scoring_profile_snapshot={"weights": {"internal_history": 0.20}},
    )
    await async_session.commit()

    retrieved = await repo.get_by_id(analysis.id)
    assert retrieved is not None
    assert len(retrieved.steps) == 1
    assert retrieved.steps[0].name == "intake_validation"
    assert retrieved.steps[0].output_summary == {"validated": True}
