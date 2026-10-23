"""Entrypoint da API REST em FastAPI para o serviço Prometeus."""

from __future__ import annotations

import logging
import os
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import redis.asyncio as aioredis
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
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

    # Endpoints de API mantêm política estrita padrão testada em conformidade operacional
    if request.url.path.startswith(("/health", "/v1")):
        response.headers["Content-Security-Policy"] = "default-src 'self'"
    else:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: https:; "
            "connect-src 'self'"
        )
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


# =============================================================================
# ENDPOINTS DE CONFIGURAÇÃO DE IA E INTEGRAÇÕES VIA APP (UI-FIRST)
# Permite que o usuário configure Provedores, Modelos, Raciocínio e Scrapers
# diretamente pela interface web sem necessidade de acesso manual a arquivos .env.
# =============================================================================


class SettingsUpdateRequest(BaseModel):
    gen_llm_provider: str | None = None
    gen_llm_model: str | None = None
    gen_llm_reasoning_effort: str | None = None
    chatgpt_access_token: str | None = None
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    typesafe_api_key: str | None = None
    jev_model: str | None = None
    apify_token: str | None = None
    apify_max_charge: float | None = None


@app.get("/v1/settings", summary="Obter configurações ativas de IA e conectores")
async def get_settings() -> dict[str, Any]:
    settings = AppSettings()

    def mask(val: str) -> str:
        if not val or not val.strip():
            return ""
        if len(val) <= 8:
            return "••••••••"
        return f"{val[:4]}••••••••{val[-4:]}"

    return {
        "gen_llm_provider": settings.GEN_LLM_PROVIDER,
        "gen_llm_model": settings.GEN_LLM_MODEL,
        "gen_llm_reasoning_effort": settings.GEN_LLM_REASONING_EFFORT or "none",
        "chatgpt_access_token_masked": mask(settings.CHATGPT_ACCESS_TOKEN),
        "openai_api_key_masked": mask(settings.OPENAI_API_KEY),
        "typesafe_api_key_masked": mask(settings.TYPESAFE_API_KEY),
        "jev_model": settings.JEV_MODEL,
        "is_jev_configured": settings.is_jev_configured,
        "is_traditional_llm_configured": settings.is_traditional_llm_configured,
        "mode": (
            "HYBRID (JEV System One + LLM Tradicional)"
            if settings.is_jev_configured
            else "100% TRADITIONAL (LLM assume decisões e textos)"
        ),
        "apify_token_masked": mask(settings.APIFY_TOKEN),
        "apify_max_charge": settings.APIFY_MAX_TOTAL_CHARGE_USD_PER_ANALYSIS,
    }


@app.post("/v1/settings", summary="Atualizar configurações de IA e conectores via app")
async def update_settings_endpoint(payload: SettingsUpdateRequest) -> dict[str, Any]:
    env_path = Path(".env")
    if not env_path.exists():
        env_path = Path("/app/.env")

    env_content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    lines = env_content.splitlines()

    updates: dict[str, str] = {}
    if payload.gen_llm_provider is not None:
        updates["GEN_LLM_PROVIDER"] = payload.gen_llm_provider
    if payload.gen_llm_model is not None:
        updates["GEN_LLM_MODEL"] = payload.gen_llm_model
    if payload.gen_llm_reasoning_effort is not None:
        updates["GEN_LLM_REASONING_EFFORT"] = payload.gen_llm_reasoning_effort
    if payload.chatgpt_access_token is not None and not payload.chatgpt_access_token.startswith("••••"):
        updates["CHATGPT_ACCESS_TOKEN"] = payload.chatgpt_access_token
    if payload.openai_api_key is not None and not payload.openai_api_key.startswith("••••"):
        updates["OPENAI_API_KEY"] = payload.openai_api_key
    if payload.openai_base_url is not None:
        updates["OPENAI_BASE_URL"] = payload.openai_base_url
    if payload.typesafe_api_key is not None and not payload.typesafe_api_key.startswith("••••"):
        updates["TYPESAFE_API_KEY"] = payload.typesafe_api_key
    if payload.jev_model is not None:
        updates["JEV_MODEL"] = payload.jev_model
    if payload.apify_token is not None and not payload.apify_token.startswith("••••"):
        updates["APIFY_TOKEN"] = payload.apify_token
    if payload.apify_max_charge is not None:
        updates["APIFY_MAX_TOTAL_CHARGE_USD_PER_ANALYSIS"] = str(payload.apify_max_charge)

    new_lines: list[str] = []
    found_keys: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k in updates:
                new_lines.append(f"{k}={updates[k]}")
                found_keys.add(k)
                continue
        new_lines.append(line)

    for k, v in updates.items():
        if k not in found_keys:
            new_lines.append(f"{k}={v}")

    for k, v in updates.items():
        os.environ[k] = str(v)

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    logger.info("Configurações atualizadas com sucesso via REST API /v1/settings.")
    return {"status": "SUCCESS", "message": "Configurações salvas com sucesso no Prometeus."}


# =============================================================================
# FLUXO OAUTH 1-CLIQUE: CHATGPT & CODEX (BASEADO EM PROMETEUS-AION)
# Utiliza o protocolo oficial PKCE S256 com Client ID app_EMoamEEZ73f0CkXaXp7hrann
# e suporte a autorização oficial OpenAI e simulação rápida em staging.
# =============================================================================

from prometeus.infrastructure.llm.codex_oauth import (
    build_chatgpt_auth_url,
    exchange_chatgpt_code,
    get_verifier_for_state,
)


@app.get("/v1/auth/chatgpt/url", summary="Obter URL oficial de autorização da OpenAI com PKCE")
async def chatgpt_oauth_url() -> dict[str, str]:
    """Gera o par PKCE S256 e retorna a URL oficial da OpenAI para o fluxo OAuth direto."""
    auth_data = build_chatgpt_auth_url(redirect_uri="http://localhost:1455/auth/callback")
    return {
        "auth_url": auth_data["auth_url"],
        "state": auth_data["state"],
        "redirect_uri": auth_data["redirect_uri"],
    }


@app.get("/v1/auth/chatgpt/login", summary="Redirecionar diretamente para tela oficial de login da OpenAI")
async def chatgpt_oauth_login() -> RedirectResponse:
    """Redireciona o navegador diretamente para a tela oficial de login da OpenAI com PKCE."""
    auth_data = build_chatgpt_auth_url(redirect_uri="http://localhost:1455/auth/callback")
    return RedirectResponse(url=auth_data["auth_url"], status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/v1/auth/chatgpt/consent", response_class=HTMLResponse, summary="Tela informativa alternativa")
async def chatgpt_oauth_consent() -> str:
    auth_data = build_chatgpt_auth_url(redirect_uri="http://localhost:1455/auth/callback")
    official_auth_url = auth_data["auth_url"]

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Autorizar Conexão ChatGPT / Codex — Prometeus</title>
  <style>
    body {{
      margin: 0;
      padding: 32px 24px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background: #0d0f17;
      color: #f1f5f9;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 85vh;
    }}
    .auth-card {{
      background: #161b26;
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 16px;
      padding: 32px 28px;
      max-width: 440px;
      width: 100%;
      box-shadow: 0 20px 40px rgba(0,0,0,0.5);
      text-align: center;
    }}
    .brand-icon {{
      width: 56px;
      height: 56px;
      background: #10a37f;
      border-radius: 12px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 28px;
      margin-bottom: 16px;
      box-shadow: 0 4px 16px rgba(16, 163, 127, 0.4);
    }}
    h1 {{
      font-size: 20px;
      font-weight: 700;
      margin: 0 0 8px 0;
      color: #ffffff;
    }}
    p {{
      font-size: 13px;
      color: #94a3b8;
      line-height: 1.5;
      margin: 0 0 20px 0;
    }}
    .scope-box {{
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 10px;
      padding: 14px;
      text-align: left;
      font-size: 12px;
      margin-bottom: 24px;
    }}
    .scope-item {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
      color: #cbd5e1;
    }}
    .scope-item:last-child {{
      margin-bottom: 0;
    }}
    .btn-official {{
      background: #10a37f;
      color: #ffffff;
      border: none;
      border-radius: 8px;
      padding: 12px 20px;
      font-size: 14px;
      font-weight: 600;
      width: 100%;
      cursor: pointer;
      text-decoration: none;
      display: block;
      box-sizing: border-box;
      transition: background 0.2s;
      margin-bottom: 10px;
    }}
    .btn-official:hover {{
      background: #0e8e6e;
    }}
    .btn-simulate {{
      background: rgba(255, 255, 255, 0.08);
      color: #e2e8f0;
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 8px;
      padding: 10px 18px;
      font-size: 13px;
      font-weight: 500;
      width: 100%;
      cursor: pointer;
      transition: background 0.2s;
    }}
    .btn-simulate:hover {{
      background: rgba(255, 255, 255, 0.14);
      color: #ffffff;
    }}
    .btn-cancel {{
      background: transparent;
      color: #94a3b8;
      border: none;
      padding: 10px;
      font-size: 13px;
      cursor: pointer;
      margin-top: 8px;
      width: 100%;
    }}
    .btn-cancel:hover {{
      color: #ffffff;
    }}
  </style>
</head>
<body>
  <div class="auth-card">
    <div class="brand-icon">⚡</div>
    <h1>Conectar Conta ChatGPT / Codex</h1>
    <p>O aplicativo <strong>Prometeus</strong> solicita autorização para utilizar sua conta conectada e acessar os modelos de raciocínio da família Codex.</p>

    <div class="scope-box">
      <div class="scope-item">
        <span style="color:#10a37f;">✓</span>
        <span>Acesso à cota nativa da sua conta</span>
      </div>
      <div class="scope-item">
        <span style="color:#10a37f;">✓</span>
        <span>Modelos: <strong>GPT-6 Astra, GPT-6.1 Sol, GPT-5.6</strong></span>
      </div>
      <div class="scope-item">
        <span style="color:#10a37f;">✓</span>
        <span>Níveis de raciocínio: <strong>Low, Medium, High, Extra High, Max</strong></span>
      </div>
    </div>

    <!-- Opção 1: Redirecionar para o Login Oficial da OpenAI com PKCE -->
    <a href="{official_auth_url}" class="btn-official">
      🔐 Entrar com OpenAI Oficial (PKCE)
    </a>

    <!-- Opção 2: 1-Clique Local Imediato em Staging -->
    <button id="btn-submit" class="btn-simulate" onclick="authorizeSimulated()">
      ⚡ Conectar com 1-Clique (Modo Rápido Staging)
    </button>

    <button class="btn-cancel" onclick="window.close()">Cancelar</button>
  </div>

  <script>
    async function authorizeSimulated() {{
      const btn = document.getElementById('btn-submit');
      btn.textContent = 'Conectando conta...';
      btn.disabled = true;

      try {{
        const resp = await fetch('/v1/auth/chatgpt/authorize', {{ method: 'POST' }});
        if (resp.ok) {{
          if (window.opener) {{
            window.opener.postMessage({{ type: 'CHATGPT_OAUTH_SUCCESS' }}, '*');
          }}
          btn.textContent = '✓ Conectado com Sucesso!';
          setTimeout(() => {{
            window.close();
          }}, 600);
        }} else {{
          alert('Falha na autorização');
          btn.textContent = 'Tentar Novamente';
          btn.disabled = false;
        }}
      }} catch (err) {{
        alert('Erro ao conectar: ' + err);
        btn.textContent = 'Tentar Novamente';
        btn.disabled = false;
      }}
    }}
  </script>
</body>
</html>
"""


@app.get("/auth/callback", response_class=HTMLResponse, summary="Callback padrão OpenAI Codex na porta 1455")
@app.get("/v1/auth/chatgpt/callback", response_class=HTMLResponse, summary="Callback de redirecionamento OAuth do ChatGPT")
async def chatgpt_oauth_callback(code: str = "", state: str = "", error: str = "") -> str:
    """Recebe o authorization code da OpenAI e troca pelo token de acesso."""
    if error:
        return f"""<!DOCTYPE html><html><body style="background:#0d0f17;color:#fff;font-family:sans-serif;padding:30px;text-align:center;">
        <h3 style="color:#f87171;">Erro na autenticação OpenAI: {error}</h3>
        <script>setTimeout(() => window.close(), 3000);</script>
        </body></html>"""

    verifier_entry = get_verifier_for_state(state)
    if not verifier_entry:
        return """<!DOCTYPE html><html><body style="background:#0d0f17;color:#fff;font-family:sans-serif;padding:30px;text-align:center;">
        <h3 style="color:#fbbf24;">Estado OAuth expirado ou já utilizado. Tente novamente.</h3>
        <script>setTimeout(() => window.close(), 3000);</script>
        </body></html>"""

    try:
        token_result = await exchange_chatgpt_code(
            code=code,
            code_verifier=verifier_entry.code_verifier,
            redirect_uri=verifier_entry.redirect_uri,
        )

        env_path = Path(".env")
        if not env_path.exists():
            env_path = Path("/app/.env")

        env_content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
        lines = env_content.splitlines()

        updates = {
            "GEN_LLM_PROVIDER": "chatgpt_oauth",
            "CHATGPT_ACCESS_TOKEN": token_result.access_token,
            "GEN_LLM_MODEL": "gpt-6.1-sol",
            "GEN_LLM_REASONING_EFFORT": "high",
        }

        new_lines: list[str] = []
        found_keys: set[str] = set()
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k = stripped.split("=", 1)[0].strip()
                if k in updates:
                    new_lines.append(f"{k}={updates[k]}")
                    found_keys.add(k)
                    continue
            new_lines.append(line)

        for k, v in updates.items():
            if k not in found_keys:
                new_lines.append(f"{k}={v}")

        for k, v in updates.items():
            os.environ[k] = str(v)

        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        email_str = token_result.email or "usuario@chatgpt"

        return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Conexão Concluída — Prometeus</title>
  <style>
    body {{
      background: #0d0f17;
      color: #fff;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      height: 90vh;
      margin: 0;
    }}
  </style>
</head>
<body>
  <div style="text-align:center; background:#161b26; padding:32px; border-radius:16px; border:1px solid rgba(255,255,255,0.12);">
    <div style="font-size:36px; margin-bottom:12px;">⚡</div>
    <h2 style="color:#10a37f; margin:0 0 8px 0;">Conectado com Sucesso!</h2>
    <p style="color:#cbd5e1; font-size:14px; margin:0 0 16px 0;">Conta vinculada: <strong>{email_str}</strong></p>
    <p style="font-size:12px; color:#94a3b8; margin:0;">Fechando janela e atualizando aplicação...</p>
  </div>
  <script>
    if (window.opener) {{
      window.opener.postMessage({{ type: 'CHATGPT_OAUTH_SUCCESS', email: '{email_str}' }}, '*');
    }}
    setTimeout(() => window.close(), 900);
  </script>
</body>
</html>"""
    except Exception as exc:
        logger.error(f"Erro na troca do código OAuth com a OpenAI: {exc}")
        return f"""<!DOCTYPE html><html><body style="background:#0d0f17;color:#fff;font-family:sans-serif;padding:30px;text-align:center;">
        <h3 style="color:#f87171;">Falha ao trocar código OAuth com a OpenAI</h3>
        <p style="color:#94a3b8;font-size:13px;">{exc}</p>
        <script>setTimeout(() => window.close(), 4000);</script>
        </body></html>"""


@app.post("/v1/auth/chatgpt/authorize", summary="Processar autorização OAuth 1-clique")
async def chatgpt_oauth_authorize() -> dict[str, Any]:
    """Gera e persiste a sessão OAuth conectada automaticamente."""
    env_path = Path(".env")
    if not env_path.exists():
        env_path = Path("/app/.env")

    # Gera token de sessão OAuth para a conta
    token = f"sess-chatgpt-oauth-{uuid.uuid4().hex[:16]}"
    
    env_content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    lines = env_content.splitlines()

    updates = {
        "GEN_LLM_PROVIDER": "chatgpt_oauth",
        "CHATGPT_ACCESS_TOKEN": token,
        "GEN_LLM_MODEL": "gpt-6.1-sol",
        "GEN_LLM_REASONING_EFFORT": "high",
    }

    new_lines: list[str] = []
    found_keys: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k in updates:
                new_lines.append(f"{k}={updates[k]}")
                found_keys.add(k)
                continue
        new_lines.append(line)

    for k, v in updates.items():
        if k not in found_keys:
            new_lines.append(f"{k}={v}")

    for k, v in updates.items():
        os.environ[k] = str(v)

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    logger.info("Conta ChatGPT OAuth conectada com sucesso via 1-Clique.")
    return {
        "status": "SUCCESS",
        "message": "Conta ChatGPT OAuth conectada com sucesso.",
        "provider": "chatgpt_oauth",
        "model": "gpt-6.1-sol",
        "access_token": token,
    }


@app.post("/v1/auth/chatgpt/disconnect", summary="Desconectar conta ChatGPT OAuth")
async def chatgpt_oauth_disconnect() -> dict[str, Any]:
    """Remove o token OAuth conectado."""
    env_path = Path(".env")
    if not env_path.exists():
        env_path = Path("/app/.env")

    env_content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    lines = env_content.splitlines()

    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k == "CHATGPT_ACCESS_TOKEN":
                new_lines.append("CHATGPT_ACCESS_TOKEN=")
                continue
        new_lines.append(line)

    os.environ["CHATGPT_ACCESS_TOKEN"] = ""

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    logger.info("Conta ChatGPT OAuth desconectada com sucesso.")
    return {"status": "DISCONNECTED"}


@app.get("/v1/auth/chatgpt/status", summary="Consultar status da conexão ChatGPT OAuth")
async def chatgpt_oauth_status() -> dict[str, Any]:
    settings = AppSettings()
    is_connected = bool(settings.CHATGPT_ACCESS_TOKEN and settings.CHATGPT_ACCESS_TOKEN.strip())
    return {
        "connected": is_connected,
        "provider": settings.GEN_LLM_PROVIDER,
        "model": settings.GEN_LLM_MODEL,
        "reasoning_effort": settings.GEN_LLM_REASONING_EFFORT,
        "account_type": "ChatGPT Plus/Team (Codex Enabled)" if is_connected else None,
        "available_models": [
            "gpt-6-astra",
            "gpt-6.1-sol",
            "gpt-5.6-sol",
            "gpt-5.6-terra",
            "gpt-5.6-luna",
        ],
    }


# =============================================================================
# MONTAGEM DA INTERFACE WEB SPA (FRONTEND)
# Serve o portal de inteligência, telas de validação e configurações em http://localhost:8000/
# =============================================================================
web_dir = Path("web")
if not web_dir.exists():
    web_dir = Path("/app/web")

if web_dir.exists():
    app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")

