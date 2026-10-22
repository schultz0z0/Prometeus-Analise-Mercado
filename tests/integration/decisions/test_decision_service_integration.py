"""Testes de integração para DecisionService: execução, persistência e circuito BLOCKED (ADR-0003)."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.application.decision_service import DecisionService
from prometeus.domain.analyses import Analysis, AnalysisStatus
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base, DecisionResultModel
from prometeus.infrastructure.jev.client import JEVServiceUnavailableError
from prometeus.infrastructure.jev.fake_client import FakeDecisionClient


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
async def test_decision_service_executes_choice_and_persists(async_session: AsyncSession) -> None:
    repo = AnalysisRepository(async_session)
    analysis = Analysis.create(
        tenant_id="ens",
        course_name="MBA em Subscrição de Riscos",
        correlation_id="corr-123",
        proposal_data={"target": "Subscritores"},
    )
    analysis.start("corr-123")
    await repo.save(analysis)
    await async_session.commit()

    fake_client = FakeDecisionClient(
        canned_choices={"readiness-v1": "READY"},
        default_confidence=0.95,
    )
    service = DecisionService(decision_model=fake_client, session=async_session)

    result = await service.execute_judgment(
        pack_id="readiness-v1",
        context={"course_name": analysis.course_name},
        analysis=analysis,
        correlation_id="corr-123",
        evidence_ids=["doc-ev-1"],
    )
    await async_session.commit()

    assert result.pack_id == "readiness-v1"
    assert result.selected_choice == "READY"
    assert result.confidence == 0.95
    assert result.requires_human_review is False

    # Verifica persistência no banco
    stmt = select(DecisionResultModel).where(DecisionResultModel.analysis_id == analysis.id)
    db_results = (await async_session.execute(stmt)).scalars().all()
    assert len(db_results) == 1
    row = db_results[0]
    assert row.pack_id == "readiness-v1"
    assert row.selected_choice == "READY"
    assert row.confidence == 0.95
    assert row.evidence_ids == ["doc-ev-1"]
    assert row.is_noul is False


@pytest.mark.asyncio
async def test_decision_service_executes_score_and_persists(async_session: AsyncSession) -> None:
    repo = AnalysisRepository(async_session)
    analysis = Analysis.create(
        tenant_id="ens",
        course_name="Especialização em Atuária",
        correlation_id="corr-456",
    )
    await repo.save(analysis)
    await async_session.commit()

    fake_client = FakeDecisionClient(
        canned_scores={"syllabus-fit-v1": 91.5},
        default_confidence=0.88,
    )
    service = DecisionService(decision_model=fake_client, session=async_session)

    result = await service.execute_judgment(
        pack_id="syllabus-fit-v1",
        context={"syllabus": "completo"},
        analysis=analysis,
        correlation_id="corr-456",
    )
    await async_session.commit()

    assert result.score_value == 91.5
    assert result.confidence == 0.88
    assert result.requires_human_review is False

    stmt = select(DecisionResultModel).where(DecisionResultModel.pack_id == "syllabus-fit-v1")
    row = (await async_session.execute(stmt)).scalar_one_or_none()
    assert row is not None
    assert row.score_value == 91.5


@pytest.mark.asyncio
async def test_decision_service_triggers_blocked_on_jev_unavailable(
    async_session: AsyncSession,
) -> None:
    """ADR-0003: Indisponibilidade do JEV aciona transição para BLOCKED com auditoria."""
    repo = AnalysisRepository(async_session)
    analysis = Analysis.create(
        tenant_id="ens",
        course_name="Curso com Falha JEV",
        correlation_id="corr-fail",
    )
    analysis.start("corr-fail")
    await repo.save(analysis)
    await async_session.commit()

    unavailable_client = FakeDecisionClient(simulate_unavailable=True)
    service = DecisionService(decision_model=unavailable_client, session=async_session)

    with pytest.raises(JEVServiceUnavailableError, match="Falha de disponibilidade do JEV"):
        await service.execute_judgment(
            pack_id="readiness-v1",
            context={},
            analysis=analysis,
            correlation_id="corr-fail",
        )

    # Análise deve ter transicionado obrigatoriamente para BLOCKED
    assert analysis.status == AnalysisStatus.BLOCKED

    # Deve conter evento de auditoria detalhando o motivo do bloqueio
    block_events = [ev for ev in analysis.audit_events if ev.to_status == AnalysisStatus.BLOCKED]
    assert len(block_events) == 1
    assert "JEV indisponível para o decision pack 'readiness-v1'" in (block_events[0].reason or "")
