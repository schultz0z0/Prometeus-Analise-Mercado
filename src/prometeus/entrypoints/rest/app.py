"""Entrypoint da API REST em FastAPI para o serviço Prometeus."""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated, Any

import redis.asyncio as aioredis
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from prometeus import __descriptor__, __product__, __version__
from prometeus.application.create_analysis import (
    CreateAnalysisCommand,
    CreateAnalysisUseCase,
)
from prometeus.domain.analyses import Analysis, DomainError
from prometeus.domain.configuration import AppSettings, ConfigurationError
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import (
    CourseOutcomeModel,
    DossierModel,
    HumanDecisionModel,
)
from prometeus.infrastructure.db.session import get_db_session, get_engine
from prometeus.observability.logging import (
    correlation_id_ctx,
    setup_logging,
)
from prometeus.workers.tasks import run_analysis_workflow

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gerencia o ciclo de vida da aplicação FastAPI."""
    settings = AppSettings()
    setup_logging(settings.LOG_LEVEL)
    logger.info(
        f"Iniciando {__product__} v{__version__} — {__descriptor__} [Env: {settings.APP_ENV}]"
    )
    yield
    logger.info(f"Encerrando {__product__}")


app = FastAPI(
    title=__product__,
    summary=__descriptor__,
    version=__version__,
    lifespan=lifespan,
)


# Middleware de Correlation ID e Problem Details
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next: Any) -> Response:
    corr_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    correlation_id_ctx.set(corr_id)
    response: Response = await call_next(request)
    response.headers["X-Correlation-ID"] = corr_id
    return response


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next: Any) -> Response:
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response


@app.exception_handler(ConfigurationError)
async def configuration_error_handler(request: Request, exc: ConfigurationError) -> JSONResponse:
    corr_id = correlation_id_ctx.get()
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "type": "urn:prometeus:problem:configuration-error",
            "title": "Erro de Configuração",
            "status": 500,
            "detail": str(exc),
            "correlation_id": corr_id,
        },
    )


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    corr_id = correlation_id_ctx.get()
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "type": "urn:prometeus:problem:domain-error",
            "title": "Violação de Regra de Negócio",
            "status": 400,
            "detail": str(exc),
            "correlation_id": corr_id,
        },
    )


class CreateAnalysisRequest(BaseModel):
    """Corpo da requisição para submeter uma análise de viabilidade."""

    course_name: str = Field(
        ...,
        description="Nome proposto para o curso",
        examples=["MBA em Gestão de Riscos e Seguros"],
    )
    tenant_id: str = Field(
        default="ens",
        description="Identificador da instituição",
        examples=["ens"],
    )
    proposal_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Dados complementares da proposta (ementa, público, preço)",
    )


class CreateAnalysisResponse(BaseModel):
    """Resposta com status 202 Accepted conforme especificação."""

    analysis_id: str
    status: str
    created_at: str
    message: str


@app.post(
    "/v1/analyses",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=CreateAnalysisResponse,
    summary="Submeter nova análise de mercado",
)
async def create_analysis(
    payload: CreateAnalysisRequest,
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            description="Chave única de idempotência obrigatória",
        ),
    ] = None,
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,  # type: ignore[assignment]
) -> CreateAnalysisResponse:
    settings = AppSettings()
    if settings.KILL_SWITCH_ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kill switch operacional ativo: submissão de novas análises suspensa temporariamente para manutenção.",
        )

    corr_id = correlation_id_ctx.get()

    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header 'Idempotency-Key' é obrigatório para criação de análises (RFC 7807).",
        )

    proposal_data = dict(payload.proposal_data)
    if settings.SHADOW_MODE:
        proposal_data["_shadow_mode"] = True

    use_case = CreateAnalysisUseCase(session)
    command = CreateAnalysisCommand(
        tenant_id=payload.tenant_id,
        course_name=payload.course_name,
        proposal_data=proposal_data,
        idempotency_key=idempotency_key.strip(),
        correlation_id=corr_id,
    )
    result = await use_case.execute(command)

    # Dispara workflow no Celery de forma assíncrona se não for requisição duplicada
    if not result.is_existing:
        try:
            run_analysis_workflow.delay(result.analysis_id, corr_id)
        except Exception as exc:
            logger.warning(
                f"Não foi possível enfileirar tarefa no Celery imediatamente: {exc}. Job mantido em QUEUED."
            )

    msg = (
        "Análise recuperada com sucesso via Idempotency-Key."
        if result.is_existing
        else "Análise aceita e enfileirada para processamento."
    )

    return CreateAnalysisResponse(
        analysis_id=result.analysis_id,
        status=result.status.value,
        created_at=result.created_at,
        message=msg,
    )


@app.get(
    "/v1/analyses/{analysis_id}",
    summary="Consultar detalhes e dossiê da análise",
)
async def get_analysis(
    analysis_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    repo = AnalysisRepository(session)
    analysis = await repo.get_by_id(analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Análise não encontrada: {analysis_id}",
        )

    return {
        "analysis_id": analysis.id,
        "tenant_id": analysis.tenant_id,
        "course_name": analysis.course_name,
        "status": analysis.status.value,
        "recommendation": analysis.recommendation.value if analysis.recommendation else None,
        "created_at": analysis.created_at.isoformat(),
        "updated_at": analysis.updated_at.isoformat(),
        "steps": [
            {
                "step_number": s.step_number,
                "name": s.name,
                "status": s.status,
                "output_summary": s.output_summary,
            }
            for s in analysis.steps
        ],
        "audit_events": [
            {
                "from_status": e.from_status.value if e.from_status else None,
                "to_status": e.to_status.value,
                "reason": e.reason,
                "correlation_id": e.correlation_id,
                "created_at": e.created_at.isoformat(),
            }
            for e in analysis.audit_events
        ],
    }


@app.get(
    "/v1/analyses/{analysis_id}/status",
    summary="Consultar ciclo de vida e recomendação",
)
async def get_analysis_status(
    analysis_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    repo = AnalysisRepository(session)
    analysis = await repo.get_by_id(analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Análise não encontrada: {analysis_id}",
        )

    return {
        "analysis_id": analysis.id,
        "status": analysis.status.value,
        "recommendation": analysis.recommendation.value if analysis.recommendation else None,
        "updated_at": analysis.updated_at.isoformat(),
    }


class ReanalyzeRequest(BaseModel):
    """Corpo da requisição para reanálise vinculada (RF-010)."""

    proposal_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Novos dados ou ajustes da proposta (ementa, preço, público)",
    )


@app.post(
    "/v1/analyses/{analysis_id}/reanalyze",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submeter reanálise vinculada (RF-010)",
)
async def reanalyze(
    analysis_id: str,
    payload: ReanalyzeRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    settings = AppSettings()
    if settings.KILL_SWITCH_ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kill switch operacional ativo: reanálise suspensa temporariamente para manutenção.",
        )

    corr_id = correlation_id_ctx.get()
    repo = AnalysisRepository(session)
    previous = await repo.get_by_id(analysis_id)
    if not previous:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Análise original não encontrada: {analysis_id}",
        )

    # Cria nova análise com herança e vínculo explícito
    new_analysis = Analysis.create(
        tenant_id=previous.tenant_id,
        course_name=previous.course_name,
        correlation_id=corr_id,
        proposal_data={**previous.proposal_data, **payload.proposal_data},
        previous_analysis_id=previous.id,
    )
    await repo.save(new_analysis)
    await session.commit()

    try:
        run_analysis_workflow.delay(new_analysis.id, corr_id)
    except Exception as exc:
        logger.warning(f"Erro ao disparar tarefa Celery para reanálise {new_analysis.id}: {exc}")

    return {
        "analysis_id": new_analysis.id,
        "previous_analysis_id": previous.id,
        "status": new_analysis.status.value,
        "message": f"Reanálise enfileirada com sucesso a partir de {previous.id}.",
    }


@app.post(
    "/v1/analyses/{analysis_id}/cancel",
    summary="Cancelar análise em andamento",
)
async def cancel_analysis(
    analysis_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    corr_id = correlation_id_ctx.get()
    repo = AnalysisRepository(session)
    analysis = await repo.get_by_id(analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Análise não encontrada: {analysis_id}",
        )

    if analysis.is_terminal:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Não é possível cancelar uma análise no estado terminal '{analysis.status.value}'.",
        )

    analysis.cancel(correlation_id=corr_id, reason="Cancelamento solicitado via API/Chatbot")
    await repo.save(analysis)
    await session.commit()

    return {
        "analysis_id": analysis.id,
        "status": analysis.status.value,
        "message": "Análise cancelada com sucesso.",
    }


@app.get(
    "/v1/analyses/{analysis_id}/dossier",
    summary="Obter dossiê estruturado e auditável (RF-012)",
)
async def get_dossier(
    analysis_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    stmt = select(DossierModel).where(DossierModel.analysis_id == analysis_id)
    dossier = (await session.execute(stmt)).scalar_one_or_none()
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dossiê ainda não gerado ou não encontrado para a análise: {analysis_id}",
        )

    return {
        "id": dossier.id,
        "analysis_id": dossier.analysis_id,
        "prompt_version": dossier.prompt_version,
        "model_name": dossier.model_name,
        "facts_hash": dossier.facts_hash,
        "status": dossier.status,
        "executive_summary": dossier.executive_summary,
        "sections": dossier.sections,
        "claims": dossier.claims,
        "cost_usd": dossier.cost_usd,
        "created_at": dossier.created_at.isoformat(),
    }


class SubmitDecisionRequest(BaseModel):
    """Corpo da requisição de decisão humana (RF-009)."""

    user_id: str = Field(..., description="ID do decisor institucional")
    user_role: str = Field(..., description="Papel do decisor (ex: director, coordinator)")
    decision: str = Field(..., description="APPROVED, APPROVED_WITH_ADJUSTMENTS, REJECTED")
    rationale: str = Field(..., description="Justificativa da decisão tomada")
    adjustments: dict[str, Any] = Field(default_factory=dict, description="Ajustes negociados")


@app.post(
    "/v1/analyses/{analysis_id}/decisions",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar decisão humana institucional (RF-009)",
)
async def submit_human_decision(
    analysis_id: str,
    payload: SubmitDecisionRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    repo = AnalysisRepository(session)
    analysis = await repo.get_by_id(analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Análise não encontrada: {analysis_id}",
        )

    model = HumanDecisionModel(
        id=f"dec_{uuid.uuid4().hex[:12]}",
        analysis_id=analysis_id,
        user_id=payload.user_id,
        user_role=payload.user_role,
        decision=payload.decision.upper(),
        rationale=payload.rationale,
        adjustments=payload.adjustments,
        created_at=datetime.now(UTC),
    )
    session.add(model)
    await session.commit()

    return {
        "decision_id": model.id,
        "analysis_id": analysis_id,
        "decision": model.decision,
        "status": "RECORDED",
        "created_at": model.created_at.isoformat(),
    }


class RecordOutcomeRequest(BaseModel):
    """Corpo da requisição de resultado pós-lançamento (RF-013)."""

    external_course_id: str = Field(..., description="Identificador do curso no LMS/CRM")
    launch_date: str = Field(..., description="Data de início de captação (AAAA-MM-DD)")
    enrolled_count: int = Field(..., ge=0, description="Total de alunos matriculados")
    leads_count: int = Field(default=0, ge=0, description="Total de leads captados")
    applicants_count: int = Field(default=0, ge=0, description="Total de inscritos")
    revenue_brl: float | None = Field(default=None, description="Receita total em BRL")
    notes: str | None = Field(default=None, description="Observações de desempenho")


@app.post(
    "/v1/analyses/{analysis_id}/outcomes",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar desfecho real de mercado pós-lançamento (RF-013)",
)
async def record_course_outcome(
    analysis_id: str,
    payload: RecordOutcomeRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    repo = AnalysisRepository(session)
    analysis = await repo.get_by_id(analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Análise não encontrada: {analysis_id}",
        )

    model = CourseOutcomeModel(
        id=f"out_{uuid.uuid4().hex[:12]}",
        analysis_id=analysis_id,
        external_course_id=payload.external_course_id,
        launch_date=payload.launch_date,
        enrolled_count=payload.enrolled_count,
        leads_count=payload.leads_count,
        applicants_count=payload.applicants_count,
        revenue_brl=payload.revenue_brl,
        notes=payload.notes,
        created_at=datetime.now(UTC),
    )
    session.add(model)
    await session.commit()

    return {
        "outcome_id": model.id,
        "analysis_id": analysis_id,
        "external_course_id": model.external_course_id,
        "enrolled_count": model.enrolled_count,
        "status": "RECORDED",
        "created_at": model.created_at.isoformat(),
    }


@app.get("/health/live", summary="Liveness probe")
async def health_live() -> dict[str, str]:
    """Verifica se o processo HTTP está ativo e respondendo."""
    return {
        "status": "live",
        "product": __product__,
        "version": __version__,
    }


@app.get("/health/ready", summary="Readiness probe")
async def health_ready() -> JSONResponse:
    """Verifica prontidão do PostgreSQL e do Redis."""
    settings = AppSettings()
    db_status = "unknown"
    redis_status = "unknown"
    is_healthy = True

    # 1. Teste do PostgreSQL
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        logger.error(f"Readiness check failed for PostgreSQL: {exc}")
        db_status = f"error: {exc}"
        is_healthy = False

    # 2. Teste do Redis
    try:
        client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        await client.ping()
        await client.close()
        redis_status = "ok"
    except Exception as exc:
        logger.error(f"Readiness check failed for Redis: {exc}")
        redis_status = f"error: {exc}"
        is_healthy = False

    resp_payload = {
        "status": "ready" if is_healthy else "degraded",
        "database": db_status,
        "redis": redis_status,
    }

    status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=resp_payload)
