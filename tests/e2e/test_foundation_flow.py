from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.application.create_analysis import (
    CreateAnalysisCommand,
    CreateAnalysisUseCase,
)
from prometeus.domain.analyses import (
    AnalysisRecommendation,
    AnalysisStatus,
    AnalysisStep,
)
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base
from prometeus.workers.tasks import WORKFLOW_STEPS, execute_workflow_steps


@pytest.fixture
async def e2e_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


async def test_e2e_resumable_job_flow_with_worker_restart(e2e_session: AsyncSession) -> None:
    """Valida o fluxo ponta a ponta da Fundação (Fase 01):

    criação -> fila -> execução parcial -> interrupção/restart do worker -> retomada -> conclusão.
    """
    repo = AnalysisRepository(e2e_session)
    use_case = CreateAnalysisUseCase(e2e_session)

    # 1. Submissão da análise
    cmd = CreateAnalysisCommand(
        tenant_id="ens",
        course_name="MBA Executivo em Fraudes e Regulação de Seguros",
        proposal_data={"target_market": "Brasil", "price": 18000},
        idempotency_key="e2e-restart-key-001",
        correlation_id="corr-e2e-root",
    )
    result = await use_case.execute(cmd)
    await e2e_session.commit()

    assert result.status == AnalysisStatus.QUEUED
    analysis_id = result.analysis_id

    # 2. Primeira execução: Worker inicia e executa até o step 2, simulando crash
    analysis = await repo.get_by_id(analysis_id)
    assert analysis is not None
    analysis.start(correlation_id="worker-run-1", reason="Worker iniciou processamento")

    # Executa step 1 e step 2 manualmente para simular progresso parcial antes do crash
    analysis.steps = [
        AnalysisStep(
            id=f"step-{step_num}",
            analysis_id=analysis_id,
            step_number=step_num,
            name=step_name,
            status="COMPLETED",
            output_summary={"checkpoint": True, "partial": True},
        )
        for step_num, step_name in WORKFLOW_STEPS[:2]
    ]
    await repo.save(analysis)
    await e2e_session.commit()

    # Verifica estado intermediário: RUNNING, 2 steps concluídos, sem recomendação
    mid_analysis = await repo.get_by_id(analysis_id)
    assert mid_analysis is not None
    assert mid_analysis.status == AnalysisStatus.RUNNING
    assert mid_analysis.recommendation is None
    assert len(mid_analysis.steps) == 2

    # 3. RESTART DO WORKER: Novo processo de worker assume a mesma tarefa
    # Invoca o motor de execução do workflow que detecta os checkpoints existentes
    await execute_workflow_steps(
        analysis_id=analysis_id,
        correlation_id="worker-run-2-post-restart",
        repository=repo,
    )
    await e2e_session.commit()

    # 4. Verificação final pós-retomada
    final_analysis = await repo.get_by_id(analysis_id)
    assert final_analysis is not None
    assert final_analysis.status == AnalysisStatus.COMPLETED
    assert final_analysis.recommendation == AnalysisRecommendation.APPROVED
    assert len(final_analysis.steps) == 4

    # Steps 1 e 2 preservaram os dados parciais do checkpoint anterior
    assert final_analysis.steps[0].output_summary.get("partial") is True
    assert final_analysis.steps[1].output_summary.get("partial") is True

    # Steps 3 e 4 foram concluídos pelo worker reiniciado
    assert final_analysis.steps[2].status == "COMPLETED"
    assert final_analysis.steps[2].output_summary.get("score") == 82.5
    assert final_analysis.steps[3].status == "COMPLETED"
    assert final_analysis.steps[3].output_summary.get("dossier_ready") is True

    # Trilha de auditoria contém toda a linha do tempo com correlation IDs distintos
    to_statuses = [e.to_status for e in final_analysis.audit_events]
    assert AnalysisStatus.QUEUED in to_statuses
    assert AnalysisStatus.RUNNING in to_statuses
    assert AnalysisStatus.COMPLETED in to_statuses
