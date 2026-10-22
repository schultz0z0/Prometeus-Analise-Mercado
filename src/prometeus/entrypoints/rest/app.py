"""Entrypoint da API REST em FastAPI para o serviço Prometeus."""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated, Any

import redis.asyncio as aioredis
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from prometeus import __descriptor__, __product__, __version__
from prometeus.application.create_analysis import (
    CreateAnalysisCommand,
    CreateAnalysisUseCase,
)
from prometeus.domain.analyses import DomainError
from prometeus.domain.configuration import AppSettings, ConfigurationError
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
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
    corr_id = correlation_id_ctx.get()

    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header 'Idempotency-Key' é obrigatório para criação de análises (RFC 7807).",
        )

    use_case = CreateAnalysisUseCase(session)
    command = CreateAnalysisCommand(
        tenant_id=payload.tenant_id,
        course_name=payload.course_name,
        proposal_data=payload.proposal_data,
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
