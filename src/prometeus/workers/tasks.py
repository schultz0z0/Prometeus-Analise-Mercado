"""Workers Celery e execução de workflow retomável com checkpoints por step."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from celery import Celery

from prometeus.domain.analyses import (
    AnalysisRecommendation,
    AnalysisStatus,
    AnalysisStep,
)
from prometeus.domain.configuration import AppSettings
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.session import get_session
from prometeus.observability.logging import correlation_id_ctx

logger = logging.getLogger(__name__)

settings = AppSettings()

# Inicialização da aplicação Celery
celery_app = Celery(
    "prometeus",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

WORKFLOW_STEPS = [
    (1, "intake_validation"),
    (2, "evidence_collection"),
    (3, "scoring_calculation"),
    (4, "dossier_compilation"),
]


async def execute_workflow_steps(
    analysis_id: str, correlation_id: str, repository: AnalysisRepository
) -> None:
    """Executa as etapas do workflow de forma determinística e retomável por checkpoint."""
    correlation_id_ctx.set(correlation_id)
    analysis = await repository.get_by_id(analysis_id)
    if not analysis:
        logger.error(f"Análise não encontrada para execução: {analysis_id}")
        return

    # Se estiver QUEUED, move para RUNNING
    if analysis.status == AnalysisStatus.QUEUED:
        analysis.start(correlation_id=correlation_id, reason="Worker iniciou execução do workflow")
        await repository.save(analysis)

    # Identifica steps já concluídos para permitir retomada idêntica (checkpointing)
    completed_step_numbers = {s.step_number for s in analysis.steps if s.status == "COMPLETED"}

    for step_num, step_name in WORKFLOW_STEPS:
        if step_num in completed_step_numbers:
            logger.info(f"Step {step_num} ({step_name}) já concluído anteriormente. Pulando.")
            continue

        logger.info(f"Executando step {step_num} ({step_name}) para análise {analysis_id}")
        now = datetime.now(UTC)

        # Encontra ou inicializa o step
        step = next((s for s in analysis.steps if s.step_number == step_num), None)
        if not step:
            step = AnalysisStep(
                id=str(uuid.uuid4()),
                analysis_id=analysis_id,
                step_number=step_num,
                name=step_name,
                status="RUNNING",
                started_at=now,
            )
            analysis.steps.append(step)
        else:
            step.status = "RUNNING"
            step.started_at = now

        await repository.save(analysis)

        # Simulação de processamento do step
        mock_output: dict[str, Any] = {
            "step": step_name,
            "processed_at": now.isoformat(),
            "status": "success",
        }
        if step_name == "scoring_calculation":
            mock_output["score"] = 82.5
        elif step_name == "dossier_compilation":
            mock_output["dossier_ready"] = True

        step.status = "COMPLETED"
        step.finished_at = datetime.now(UTC)
        step.output_summary = mock_output
        await repository.save(analysis)

    # Conclui a análise e registra a recomendação determinística do motor
    if analysis.status == AnalysisStatus.RUNNING:
        analysis.complete(
            recommendation=AnalysisRecommendation.APPROVED,
            correlation_id=correlation_id,
            reason="Todas as etapas do workflow executadas e verificadas",
        )
        await repository.save(analysis)
        logger.info(
            f"Análise {analysis_id} concluída com sucesso com recomendação {analysis.recommendation}"
        )


@celery_app.task(name="prometeus.run_analysis_workflow")
def run_analysis_workflow(analysis_id: str, correlation_id: str) -> dict[str, str]:
    """Tarefa Celery que aciona a execução do workflow de forma assíncrona."""

    async def _runner() -> None:
        async with get_session() as session:
            repo = AnalysisRepository(session)
            await execute_workflow_steps(analysis_id, correlation_id, repo)

    asyncio.run(_runner())
    return {"analysis_id": analysis_id, "status": "COMPLETED"}
