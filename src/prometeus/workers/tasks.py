"""Entrada Celery fina para o workflow canônico de auditoria de cursos."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from contextlib import suppress

from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from prometeus.application.analysis_jobs import (
    claim_analysis_job,
    finish_analysis_job,
    reconcile_analysis_jobs,
    renew_analysis_job,
    schedule_analysis_job_retry,
)
from prometeus.application.analysis_webhooks import deliver_pending_webhooks
from prometeus.application.recover_market_collection import CollectionRetryScheduled
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
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    beat_schedule={"recover-analysis-jobs": {"task": "prometeus.reconcile_jobs", "schedule": 15.0}},
)


async def execute_workflow_steps(
    analysis_id: str,
    correlation_id: str,
    repository: AnalysisRepository,
    use_case: RunCourseAnalysis | None = None,
    runtime_settings: AppSettings | None = None,
    execution_guard: Callable[[], Awaitable[None]] | None = None,
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
        cancellation_check=lambda: _analysis_active(repository, analysis_id),
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
        workflow.execution_guard = execution_guard
        await workflow.execute(analysis_id, correlation_id)
    finally:
        await apify.aclose()


async def _analysis_active(repository: AnalysisRepository, analysis_id: str) -> bool:
    from sqlalchemy import select

    from prometeus.infrastructure.db.models import AnalysisModel

    value = await repository.session.scalar(
        select(AnalysisModel.status).where(AnalysisModel.id == analysis_id)
    )
    return value not in {None, "CANCELLED", "FAILED", "COMPLETED"}


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
                token = uuid.uuid4().hex
                if not await claim_analysis_job(session, analysis_id, token):
                    return "ALREADY_CLAIMED"

                async def lease_guard() -> None:
                    from datetime import UTC, datetime

                    from sqlalchemy import select

                    from prometeus.domain.analyses import WorkflowStoppedError
                    from prometeus.infrastructure.db.models import AnalysisJobModel

                    async with session_factory() as guard_session:
                        owned = await guard_session.scalar(
                            select(AnalysisJobModel.analysis_id).where(
                                AnalysisJobModel.analysis_id == analysis_id,
                                AnalysisJobModel.lease_token == token,
                                AnalysisJobModel.status == "RUNNING",
                                AnalysisJobModel.lease_expires_at > datetime.now(UTC),
                            )
                        )
                        if owned is None:
                            raise WorkflowStoppedError(
                                "Lease de execução perdido; interromper chamadas externas."
                            )

                workflow_task = asyncio.create_task(
                    execute_workflow_steps(
                        analysis_id, correlation_id, repository, execution_guard=lease_guard
                    )
                )

                async def heartbeat() -> None:
                    while True:
                        await asyncio.sleep(30)
                        try:
                            async with session_factory() as lease_session:
                                if await renew_analysis_job(lease_session, analysis_id, token):
                                    continue
                        except Exception:
                            pass
                        workflow_task.cancel()
                        return

                task = asyncio.create_task(heartbeat())
                try:
                    await workflow_task
                except CollectionRetryScheduled as exc:
                    scheduled = await schedule_analysis_job_retry(
                        session, analysis_id, token, exc.next_attempt_at
                    )
                    return "RETRY_SCHEDULED" if scheduled else "LEASE_LOST_OR_STOPPED"
                except asyncio.CancelledError:
                    return "LEASE_LOST"
                finally:
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        await task
                analysis = await repository.get_by_id(analysis_id)
                if analysis is not None and analysis.status.value != "RUNNING":
                    await finish_analysis_job(session, analysis_id, token)
                return analysis.status.value if analysis is not None else "NOT_FOUND"
        finally:
            await engine.dispose()

    status = asyncio.run(_runner())
    return {"analysis_id": analysis_id, "status": status}


@celery_app.task(name="prometeus.reconcile_jobs")
def reconcile_jobs() -> dict[str, int]:
    async def run() -> dict[str, int]:
        runtime_settings = AppSettings()
        engine = get_engine(runtime_settings.DATABASE_URL, poolclass=NullPool)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with factory() as session:
                published = await reconcile_analysis_jobs(session, run_analysis_workflow.delay)
                delivered = await deliver_pending_webhooks(session, runtime_settings)
                return {"published": published, "webhooks_attempted": delivered}
        finally:
            await engine.dispose()

    return asyncio.run(run())
