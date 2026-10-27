"""Entrada Celery fina para o workflow canônico de auditoria de cursos."""

from __future__ import annotations

import asyncio

from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from prometeus.application.run_course_analysis import (
    WORKFLOW_STEPS,
    RunCourseAnalysis,
)
from prometeus.application.runtime_preflight import validate_runtime_preflight
from prometeus.domain.configuration import AppSettings, ConfigurationError
from prometeus.infrastructure.apify.client import ApifyClient
from prometeus.infrastructure.apify.registry import ActorConfigurationError, ApifyActorRegistry
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.session import get_engine
from prometeus.infrastructure.factory import get_decision_model, get_generative_model

__all__ = ["WORKFLOW_STEPS", "celery_app", "execute_workflow_steps", "run_analysis_workflow"]

settings = AppSettings()

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


async def execute_workflow_steps(
    analysis_id: str,
    correlation_id: str,
    repository: AnalysisRepository,
    use_case: RunCourseAnalysis | None = None,
    runtime_settings: AppSettings | None = None,
) -> None:
    """Executa o workflow real; a injeção opcional existe apenas para testes."""
    if use_case is not None:
        await use_case.execute(analysis_id, correlation_id)
        return

    runtime_settings = runtime_settings or AppSettings()
    preflight = validate_runtime_preflight(runtime_settings)
    if not preflight.ready:
        reason = "; ".join(f"{issue.code}: {issue.message}" for issue in preflight.errors)
        analysis = await repository.get_by_id(analysis_id)
        if analysis is not None:
            if analysis.status.value == "QUEUED":
                analysis.start(correlation_id, reason="Preflight de runtime iniciado")
            if analysis.status.value == "RUNNING":
                analysis.block(correlation_id, reason=reason)
            await repository.save(analysis)
            await repository.session.commit()
        return

    try:
        registry = ApifyActorRegistry.from_settings(runtime_settings)
        llm = get_generative_model(runtime_settings)
        decision_model = get_decision_model(runtime_settings)
    except (ConfigurationError, ActorConfigurationError) as exc:
        analysis = await repository.get_by_id(analysis_id)
        if analysis is not None:
            if analysis.status.value == "QUEUED":
                analysis.start(correlation_id, reason="Construção segura dos provedores iniciada")
            if analysis.status.value == "RUNNING":
                analysis.block(correlation_id, reason=f"runtime_provider_error: {exc}")
            await repository.save(analysis)
            await repository.session.commit()
        return

    apify = ApifyClient(
        api_token=runtime_settings.APIFY_TOKEN,
        registry=registry,
        base_url=runtime_settings.APIFY_BASE_URL,
        timeout_seconds=float(runtime_settings.GEN_LLM_TIMEOUT_SECONDS),
    )
    try:
        workflow = RunCourseAnalysis(
            session=repository.session,
            settings=runtime_settings,
            llm=llm,
            decision_model=decision_model,
            tool_executor=apify,
            registry=registry,
        )
        await workflow.execute(analysis_id, correlation_id)
    finally:
        await apify.aclose()


@celery_app.task(name="prometeus.run_analysis_workflow")
def run_analysis_workflow(analysis_id: str, correlation_id: str) -> dict[str, str]:
    """Abre uma transação local e delega integralmente ao caso de uso canônico."""

    async def _runner() -> str:
        engine = get_engine(settings.DATABASE_URL, poolclass=NullPool)
        session_factory = async_sessionmaker(
            bind=engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )
        try:
            async with session_factory() as session:
                repository = AnalysisRepository(session)
                await execute_workflow_steps(analysis_id, correlation_id, repository)
                analysis = await repository.get_by_id(analysis_id)
                return analysis.status.value if analysis is not None else "NOT_FOUND"
        finally:
            await engine.dispose()

    status = asyncio.run(_runner())
    return {"analysis_id": analysis_id, "status": status}
