"""Entrypoint da API REST em FastAPI para o serviço Prometeus."""

from __future__ import annotations

import asyncio
import base64
import html
import io
import json
import logging
import os
import re
import time
import uuid
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import urlencode

import redis.asyncio as aioredis
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pypdf import PdfReader
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from prometeus import __descriptor__, __product__, __version__
from prometeus.application.analysis_jobs import publish_analysis_job
from prometeus.application.create_analysis import (
    CreateAnalysisCommand,
    CreateAnalysisUseCase,
)
from prometeus.application.runtime_preflight import validate_runtime_preflight
from prometeus.application.sector_radar import SectorRadarService, serialize_radar_snapshot
from prometeus.domain.analyses import AnalysisStatus, DomainError
from prometeus.domain.configuration import (
    AppSettings,
    ConfigurationError,
    TenantConfig,
    TenantNotFoundError,
    resolve_tenant_config_for_id,
)
from prometeus.infrastructure.access import (
    COOKIE_NAME,
    AccessPrincipal,
    authenticate_key,
    authenticated_principal,
    create_browser_session,
    operation_scope,
    require_same_origin,
)
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import (
    AnalysisModel,
    CourseOutcomeModel,
    DossierAreaReviewModel,
    DossierModel,
    HistoricalCourseModel,
    HistoricalFunnelModel,
    HumanDecisionModel,
    MarketEvidenceModel,
    ScoringResultModel,
    ToolRunAttemptModel,
    ToolRunModel,
)
from prometeus.infrastructure.db.session import get_db_session, get_engine
from prometeus.infrastructure.llm.client import ChatGPTPlanGenerativeClient
from prometeus.infrastructure.llm.codex_oauth import (
    DIRECT_USAGE_SCOPE,
    DYNAMIC_CLIENT_ID,
    REASONING_EFFORTS,
    ChatGPTCredentials,
    ChatGPTCredentialStore,
    build_chatgpt_auth_url,
    exchange_chatgpt_code,
    get_verifier_for_state,
    list_chatgpt_models,
    public_chatgpt_model,
    refresh_chatgpt_tokens,
)
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
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: https:; "
            "connect-src 'self'"
        )
    return response


@app.middleware("http")
async def access_control_middleware(request: Request, call_next: Any) -> Response:
    path = request.url.path
    if not path.startswith("/v1/") or path == "/v1/session/login":
        return await call_next(request)  # type: ignore[no-any-return]
    try:
        principal, cookie_auth = authenticated_principal(request, AppSettings())
        principal.require(operation_scope(request))
        if cookie_auth and request.method not in {"GET", "HEAD", "OPTIONS"}:
            require_same_origin(request)
        tenant_ids = request.query_params.getlist("tenant_id")
        tenant_path = re.match(r"^/v1/tenants/([^/]+)", path)
        if tenant_path:
            tenant_ids.append(tenant_path.group(1))
        if request.method in {"POST", "PUT", "PATCH"} and request.headers.get(
            "content-type", ""
        ).startswith("application/json"):
            try:
                body = await request.json()
            except json.JSONDecodeError:
                body = {}
            if isinstance(body, dict) and body.get("tenant_id"):
                tenant_ids.append(str(body["tenant_id"]))
            elif path == "/v1/analyses":
                tenant_ids.append("ens")  # Mesmo default do contrato CreateAnalysisRequest.
        if not tenant_ids and (path == "/v1/analyses" or path.startswith("/v1/institutional/")):
            request.scope["query_string"] = urlencode(
                [*request.query_params.multi_items(), ("tenant_id", principal.tenant_id)]
            ).encode()
        if any(tenant_id != principal.tenant_id for tenant_id in tenant_ids):
            raise HTTPException(403, "Acesso a outra instituição não autorizado.")
        resource = re.match(r"^/v1/analyses/([^/]+)", path)
        if resource:
            dependency = app.dependency_overrides.get(get_db_session, get_db_session)
            async for session in dependency():
                owner = await session.scalar(
                    select(AnalysisModel.tenant_id).where(AnalysisModel.id == resource.group(1))
                )
                if owner is not None and owner != principal.tenant_id:
                    raise HTTPException(403, "Acesso a outra instituição não autorizado.")
        request.state.principal = principal
        return await call_next(request)  # type: ignore[no-any-return]
    except HTTPException as error:
        return JSONResponse(
            status_code=error.status_code, content={"detail": error.detail}, headers=error.headers
        )


class LoginRequest(BaseModel):
    access_key: str = Field(min_length=1, max_length=4096)


@app.post("/v1/session/login")
async def login_session(
    payload: LoginRequest, request: Request, response: Response
) -> dict[str, str]:
    require_same_origin(request)
    settings = AppSettings()
    principal = authenticate_key(payload.access_key, settings)
    response.set_cookie(
        COOKIE_NAME,
        create_browser_session(principal, settings),
        httponly=True,
        samesite="strict",
        secure=request.url.scheme == "https",
        max_age=28800,
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return principal.public()


@app.get("/v1/session")
async def get_browser_session(request: Request) -> dict[str, str]:
    principal: AccessPrincipal = request.state.principal
    return principal.public()


@app.post("/v1/session/logout")
async def logout_session(response: Response) -> dict[str, str]:
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"status": "signed_out"}


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

    use_case = CreateAnalysisUseCase(session, settings)
    command = CreateAnalysisCommand(
        tenant_id=payload.tenant_id,
        course_name=payload.course_name,
        proposal_data=proposal_data,
        idempotency_key=idempotency_key.strip(),
        correlation_id=corr_id,
    )
    result = await use_case.execute(command)
    # A análise, snapshot e outbox ficam visíveis antes de qualquer publicação.
    await session.commit()

    # Dispara workflow no Celery de forma assíncrona se não for requisição duplicada
    if not result.is_existing:
        await publish_analysis_job(session, result.analysis_id, run_analysis_workflow.delay)

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


class ExtractDocumentRequest(BaseModel):
    filename: str
    content_base64: str


def _extract_docx_text(raw_bytes: bytes) -> str:
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
        xml_bytes = zf.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    lines: list[str] = []
    body = root.find("w:body", ns)
    target = body if body is not None else root
    for child in target:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            texts = [t.text for t in child.findall(".//w:t", ns) if t.text]
            line = "".join(texts).strip()
            if line:
                lines.append(line)
        elif tag == "tbl":
            for tr in child.findall(".//w:tr", ns):
                cells: list[str] = []
                for tc in tr.findall(".//w:tc", ns):
                    cell_text = " ".join(
                        "".join(t.text for t in p.findall(".//w:t", ns) if t.text).strip()
                        for p in tc.findall(".//w:p", ns)
                    ).strip()
                    if cell_text:
                        cells.append(cell_text)
                if cells:
                    lines.append(" | ".join(cells))
    return "\n".join(lines)


@app.post(
    "/v1/intake/extract-document",
    summary="Extrair texto de PDF, DOCX ou TXT para o formulário de intake",
)
async def extract_intake_document(payload: ExtractDocumentRequest) -> dict[str, str]:
    try:
        b64 = payload.content_base64.split(",", 1)[-1].strip()
        raw_bytes = base64.b64decode(b64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Arquivo base64 inválido: {exc}") from exc

    fname = payload.filename.lower()
    if len(raw_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="O documento deve ter até 10 MB.")
    if fname.endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(raw_bytes))
            if reader.is_encrypted or len(reader.pages) > 100:
                raise ValueError("PDF protegido ou com mais de 100 páginas.")
            extracted = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail="Não foi possível ler o PDF. Use um PDF válido, sem senha, com até 100 páginas.",
            ) from exc
        if not extracted:
            raise HTTPException(
                status_code=422,
                detail="O PDF não contém texto extraível. Cole a ementa no formulário ou use um documento com texto selecionável.",
            )
    elif fname.endswith(".docx"):
        try:
            extracted = _extract_docx_text(raw_bytes)
        except Exception as exc:
            raise HTTPException(
                status_code=400, detail=f"Não foi possível ler o arquivo DOCX: {exc}"
            ) from exc
    else:
        extracted = raw_bytes.decode("utf-8", errors="replace").strip()

    return {"filename": payload.filename, "text": extracted}


AREA_REVIEW_STATUS_META: dict[str, dict[str, str]] = {
    "APPROVED": {"label": "Aprovado", "tone": "approved"},
    "IN_REVIEW": {"label": "Em revisão", "tone": "adjustments"},
    "CHANGES_REQUESTED": {"label": "Ajustes solicitados", "tone": "risk"},
    "PENDING": {"label": "Pendente", "tone": "insufficient"},
}

AREA_LABELS_BY_KEY: dict[str, str] = {
    "marketing": "Marketing",
    "produto": "Produto",
    "comercial": "Comercial",
    "financeiro": "Financeiro",
}


async def _load_area_reviews(
    session: AsyncSession,
    analysis_id: str,
) -> list[DossierAreaReviewModel]:
    stmt = (
        select(DossierAreaReviewModel)
        .where(DossierAreaReviewModel.analysis_id == analysis_id)
        .order_by(DossierAreaReviewModel.created_at, DossierAreaReviewModel.id)
    )
    return list((await session.execute(stmt)).scalars().all())


def _apply_area_reviews_to_revisions_page(
    revisions_page: dict[str, Any],
    area_reviews: list[DossierAreaReviewModel],
) -> dict[str, Any]:
    updated_page: dict[str, Any] = json.loads(json.dumps(revisions_page))
    area_cards = list(updated_page.get("area_reviews") or [])

    latest_by_area: dict[str, DossierAreaReviewModel] = {}
    for review in area_reviews:
        latest_by_area[review.area.lower()] = review

    approved_count = 0
    for card in area_cards:
        area_key = str(card.get("area") or "").lower()
        rev = latest_by_area.get(area_key)
        if rev:
            meta = AREA_REVIEW_STATUS_META.get(
                rev.status.upper(), {"label": rev.status, "tone": "insufficient"}
            )
            card["status"] = rev.status.upper()
            card["status_label"] = meta["label"]
            card["tone"] = meta["tone"]
            card["reviewer_name"] = rev.reviewer_name
            card["updated_at_label"] = rev.created_at.strftime("%d/%m/%Y, %H:%M")
            card["comment"] = rev.comment
        if str(card.get("status") or "").upper() == "APPROVED":
            approved_count += 1

    total_areas = max(1, len(area_cards) or 4)
    pct = round((approved_count / total_areas) * 100)
    if approved_count == total_areas:
        overall_label = "Homologado pelas áreas"
        overall_tone = "approved"
    elif approved_count > 0 or area_reviews:
        overall_label = "Em revisão"
        overall_tone = "adjustments"
    else:
        overall_label = "Aguardando aprovação das áreas"
        overall_tone = "insufficient"

    updated_page["area_reviews"] = area_cards
    updated_page["overall_progress"] = {
        "approved_count": approved_count,
        "total_areas": total_areas,
        "percent": pct,
        "status_label": overall_label,
        "tone": overall_tone,
    }

    base_version = {
        "version": "v1.0",
        "is_current": len(area_reviews) == 0,
        "badge_label": "Base",
        "tone": "insufficient" if area_reviews else "approved",
        "timestamp_label": "Publicação inicial verificada",
        "description": "Primeira versão do dossiê consolidada e auditada pelo verificador determinístico.",
    }
    versions: list[dict[str, Any]] = []
    for idx, rev in enumerate(area_reviews, start=1):
        is_latest = idx == len(area_reviews)
        area_lbl = AREA_LABELS_BY_KEY.get(rev.area.lower(), rev.area)
        meta = AREA_REVIEW_STATUS_META.get(
            rev.status.upper(), {"label": rev.status, "tone": "adjustments"}
        )
        versions.append(
            {
                "version": rev.version_label or f"v1.{idx}",
                "is_current": is_latest,
                "badge_label": "Atual" if is_latest else "Revisada",
                "tone": meta["tone"],
                "timestamp_label": rev.created_at.strftime("%d/%m/%Y, %H:%M"),
                "description": f"{area_lbl} ({rev.reviewer_name}): {rev.comment or meta['label']}",
            }
        )
    versions.reverse()
    versions.append(base_version)
    updated_page["version_history"] = versions

    comments_feed: list[dict[str, Any]] = []
    for rev in reversed(area_reviews):
        area_lbl = AREA_LABELS_BY_KEY.get(rev.area.lower(), rev.area)
        meta = AREA_REVIEW_STATUS_META.get(
            rev.status.upper(), {"label": rev.status, "tone": "adjustments"}
        )
        initials = "".join(part[0].upper() for part in rev.reviewer_name.split()[:2] if part) or "EN"
        comments_feed.append(
            {
                "id": rev.id,
                "reviewer_name": rev.reviewer_name,
                "initials": initials,
                "area": rev.area.lower(),
                "area_label": area_lbl,
                "status": rev.status.upper(),
                "status_label": meta["label"],
                "tone": meta["tone"],
                "timestamp_label": rev.created_at.strftime("%d/%m/%Y, %H:%M"),
                "comment": rev.comment or f"Parecer registrado: {meta['label']}.",
            }
        )
    updated_page["comments_feed"] = comments_feed
    return updated_page


def _public_evidence_payload(data: dict[str, Any] | None) -> dict[str, Any]:
    # Checkpoints contain the entire delivered corpus and stay server-side.
    return {key: value for key, value in (data or {}).items() if key != "_reading"}


def _cms_evidence_admitted(data: dict[str, Any] | None) -> bool:
    qualification = (data or {}).get("_qualification")
    return not isinstance(qualification, dict) or not qualification or (
        qualification.get("accepted") is True or qualification.get("context_only") is True
    )


def _hydrate_dossier_presentation(
    *,
    analysis_id: str,
    course_name: str,
    proposal: dict[str, Any],
    dossier: DossierModel,
    scoring: ScoringResultModel | None,
    evidences: list[MarketEvidenceModel],
    area_reviews: list[DossierAreaReviewModel],
) -> dict[str, Any]:
    from prometeus.application.dossier_cms_builder import build_cms_dossier_pages
    from prometeus.application.ecosystem_presentation import build_ecosystem_presentation_blocks
    from prometeus.application.synthesize_dossier import DossierSynthesisService
    from prometeus.domain.dossiers import (
        DossierClaim,
        DossierFactItem,
        DossierFacts,
        DossierHighlights,
        DossierOutput,
        DossierSection,
    )

    presentation = dict(dossier.presentation or {})
    stored_revisions = ((presentation.get("cms_pages") or {}).get("pages") or {}).get("revisions")

    pillar_summaries: dict[str, float] = {}
    pillar_details: dict[str, Any] = {}
    if scoring and isinstance(scoring.pillar_scores, dict):
        for k, val in scoring.pillar_scores.items():
            if isinstance(val, dict):
                pillar_details[k] = val
                if isinstance(val.get("raw_score"), (int, float)):
                    pillar_summaries[k] = float(val["raw_score"])
            elif isinstance(val, (int, float)):
                pillar_summaries[k] = float(val)

    fact_items = [
        DossierFactItem(
            evidence_id=ev.id,
            source_type=ev.evidence_type,
            title=ev.title,
            key_metrics={
                **_public_evidence_payload(ev.sanitized_data),
                **({"evidence_role": "context_only"}
                   if (ev.sanitized_data or {}).get("_qualification", {}).get("context_only") is True else {}),
            },
            summary=ev.title,
            source_url=ev.source_url,
        )
        for ev in evidences
        if _cms_evidence_admitted(ev.sanitized_data)
    ]
    facts = DossierFacts(
        analysis_id=analysis_id,
        course_name=course_name,
        target_audience=str(proposal.get("audience") or "Profissionais do setor"),
        recommendation=(scoring.recommendation if scoring else "REQUIRES_HUMAN_REVIEW"),
        viability_score=float(scoring.viability_score if scoring else 0.0),
        coverage_score=float(scoring.coverage_score if scoring else 0.0),
        confidence_score=float(scoring.confidence_score if scoring else 0.0),
        pillar_summaries=pillar_summaries,
        pillar_details=pillar_details,
        items=fact_items,
        limitations=list(presentation.get("limitations") or []),
        counterevidence=list(presentation.get("counterevidence") or []),
        analysis_audit=dict(presentation.get("analysis_audit") or {}),
    )
    raw_highlights = presentation.get("highlights")
    try:
        highlights_obj = (
            DossierHighlights.model_validate(raw_highlights)
            if isinstance(raw_highlights, dict)
            else DossierHighlights()
        )
    except Exception:
        highlights_obj = DossierHighlights()

    claims_objs: list[DossierClaim] = []
    for raw_claim in dossier.claims or []:
        if isinstance(raw_claim, dict):
            try:
                claims_objs.append(DossierClaim.model_validate(raw_claim))
            except Exception:
                continue

    sections_objs: list[DossierSection] = []
    for raw_sec in dossier.sections or []:
        if isinstance(raw_sec, dict):
            try:
                sections_objs.append(DossierSection.model_validate(raw_sec))
            except Exception:
                continue

    dossier_obj = DossierOutput(
        id=dossier.id,
        analysis_id=analysis_id,
        prompt_version=dossier.prompt_version,
        model_name=dossier.model_name,
        executive_summary=dossier.executive_summary,
        executive_summary_claim_ids=list(presentation.get("executive_summary_claim_ids") or []),
        highlights=highlights_obj,
        sections=sections_objs,
        claims=claims_objs,
        facts_hash=dossier.facts_hash,
    )
    economics = presentation.get("economics") or DossierSynthesisService._build_economics_presentation(proposal)
    workload = proposal.get("workload_hours")
    safe_workload = workload if isinstance(workload, int) and not isinstance(workload, bool) and workload > 0 else 0
    ecosystem = {
        "competitive_benchmark": presentation.get("competitive_benchmark"),
        "sector_radar": presentation.get("sector_radar"),
    }
    if not ecosystem["competitive_benchmark"] and not ecosystem["sector_radar"]:
        ecosystem = build_ecosystem_presentation_blocks(proposal, facts, safe_workload)
    rebuilt_cms = build_cms_dossier_pages(
        proposal=proposal,
        facts=facts,
        dossier=dossier_obj,
        economics=economics,
        ecosystem=ecosystem,
    )
    if isinstance(stored_revisions, dict) and not area_reviews and len(stored_revisions.get("version_history") or []) > 1:
        rebuilt_cms["pages"]["revisions"] = dict(stored_revisions)
    presentation["cms_pages"] = rebuilt_cms

    cms_pages = dict(presentation.get("cms_pages") or {})
    pages = dict(cms_pages.get("pages") or {})
    if "revisions" in pages:
        pages["revisions"] = _apply_area_reviews_to_revisions_page(pages["revisions"], area_reviews)
        cms_pages["pages"] = pages
        presentation["cms_pages"] = cms_pages

    return presentation


@app.get(
    "/v1/analyses",
    summary="Listar análises e dossiês verificados do tenant",
)
async def list_analyses(
    tenant_id: str = "ens",
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    stmt = (
        select(AnalysisModel)
        .where(AnalysisModel.tenant_id == tenant_id)
        .order_by(AnalysisModel.created_at.desc())
        .limit(50)
    )
    rows = (await session.execute(stmt)).scalars().all()
    items: list[dict[str, Any]] = []
    repo = AnalysisRepository(session)
    for row in rows:
        domain_analysis = await repo.get_by_id(row.id)
        proposal = domain_analysis.proposal_data if domain_analysis else {}
        dossier_stmt = select(DossierModel).where(DossierModel.analysis_id == row.id)
        dossier = (await session.execute(dossier_stmt)).scalar_one_or_none()
        scoring_stmt = select(ScoringResultModel).where(ScoringResultModel.analysis_id == row.id)
        scoring = (await session.execute(scoring_stmt)).scalar_one_or_none()
        dossier_payload: dict[str, Any] | None = None
        if dossier and scoring and dossier.status == "VERIFIED":
            ev_stmt = select(MarketEvidenceModel).where(MarketEvidenceModel.analysis_id == row.id)
            evidences = list((await session.execute(ev_stmt)).scalars().all())
            area_reviews = await _load_area_reviews(session, row.id)
            hydrated_presentation = _hydrate_dossier_presentation(
                analysis_id=row.id,
                course_name=row.course_name,
                proposal=proposal,
                dossier=dossier,
                scoring=scoring,
                evidences=evidences,
                area_reviews=area_reviews,
            )
            dossier_payload = {
                "id": dossier.id,
                "analysis_id": dossier.analysis_id,
                "prompt_version": dossier.prompt_version,
                "model_name": dossier.model_name,
                "facts_hash": dossier.facts_hash,
                "status": dossier.status,
                "executive_summary": dossier.executive_summary,
                "schema_version": hydrated_presentation.get("schema_version", 1),
                "executive_summary_claim_ids": hydrated_presentation.get(
                    "executive_summary_claim_ids", []
                ),
                "highlights": hydrated_presentation.get("highlights", {}),
                "limitations": hydrated_presentation.get("limitations", []),
                "analysis_audit": hydrated_presentation.get("analysis_audit", {}),
                "three_fold_review": hydrated_presentation.get("three_fold_review"),
                "presentation": hydrated_presentation,
                "sections": dossier.sections,
                "claims": dossier.claims,
                "cost_usd": dossier.cost_usd,
                "created_at": dossier.created_at.isoformat(),
                "scoring": {
                    "viability_score": scoring.viability_score,
                    "profile_id": scoring.profile_id,
                    "partial_score": scoring.partial_score,
                    "coverage_score": scoring.coverage_score,
                    "confidence_score": scoring.confidence_score,
                    "recommendation": scoring.recommendation,
                    "pillar_scores": scoring.pillar_scores,
                    "gate_details": scoring.gate_details,
                    "is_experimental": scoring.is_experimental,
                },
                "evidences": [
                    {
                        "id": ev.id,
                        "evidence_type": ev.evidence_type,
                        "source_name": ev.source_name,
                        "source_url": ev.source_url,
                        "collector": ev.collector,
                        "title": ev.title,
                        "sanitized_data": _public_evidence_payload(ev.sanitized_data),
                        "quality_score": ev.quality_score,
                        "cost_usd": ev.cost_usd,
                        "collected_at": ev.collected_at.isoformat(),
                    }
                    for ev in evidences
                ],
            }
        items.append(
            {
                "id": row.id,
                "name": row.course_name,
                "area": proposal.get("area") or "Não informada",
                "level": proposal.get("level") or "Não informado",
                "modality": proposal.get("modality") or "Não informada",
                "ticket": proposal.get("ticket"),
                "price_period": proposal.get("price_period") or "unknown",
                "duration_months": proposal.get("duration_months"),
                "status": row.status,
                "recommendation": scoring.recommendation if scoring else row.recommendation,
                "viability_score": scoring.viability_score if scoring else None,
                "coverage_index": scoring.coverage_score if scoring else None,
                "confidence_index": scoring.confidence_score if scoring else None,
                "created_at": row.created_at.isoformat(),
                "dossier": dossier_payload,
            }
        )
    return {"tenant_id": tenant_id, "items": items}


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

    tool_runs = (
        (
            await session.execute(
                select(ToolRunModel)
                .where(ToolRunModel.analysis_id == analysis_id)
                .order_by(ToolRunModel.started_at, ToolRunModel.id)
            )
        )
        .scalars()
        .all()
    )
    from prometeus.application.evidence_reading_audit import summarize_reading_audit

    reading_evidences = list((await session.scalars(
        select(MarketEvidenceModel).where(MarketEvidenceModel.analysis_id == analysis_id)
    )).all())
    reading_audit = summarize_reading_audit(
        [{"id": run.id, "provider_run_id": run.provider_run_id,
          "dataset_id": run.dataset_id, "parameters": run.parameters} for run in tool_runs],
        [{"id": row.id, "sanitized_data": row.sanitized_data} for row in reading_evidences],
    )
    attempts = list((await session.execute(
        select(ToolRunAttemptModel)
        .where(ToolRunAttemptModel.analysis_id == analysis_id,
               ToolRunAttemptModel.tenant_id == analysis.tenant_id)
        .order_by(ToolRunAttemptModel.attempt_index)
    )).scalars())
    attempts_by_run: dict[str, list[dict[str, Any]]] = {}

    def diagnostic_code(diagnostic: dict[str, Any], key: str) -> str | None:
        # Only structured identifiers leave the backend; no input snapshots or logs.
        value = diagnostic.get(key)
        return value if isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,63}", value) else None

    for attempt in attempts:
        diagnostic = attempt.diagnosis or {}
        attempts_by_run.setdefault(attempt.tool_run_id, []).append({
            "attempt_index": attempt.attempt_index,
            "status": attempt.status,
            "run_id": attempt.provider_run_id,
            "dataset_id": attempt.dataset_id,
            "cost_usd": attempt.cost_usd,
            "cause": diagnostic_code(diagnostic, "cause"),
            "action": diagnostic_code(diagnostic, "action"),
            "started_at": attempt.started_at.isoformat(),
            "finished_at": attempt.finished_at.isoformat() if attempt.finished_at else None,
            "next_attempt_at": attempt.next_attempt_at.isoformat() if attempt.next_attempt_at else None,
        })
    blocking_event = next(
        (event for event in reversed(analysis.audit_events) if event.to_status.value == "BLOCKED"),
        None,
    )

    return {
        "analysis_id": analysis.id,
        "tenant_id": analysis.tenant_id,
        "course_name": analysis.course_name,
        "reading_audit": reading_audit,
        "status": analysis.status.value,
        "recommendation": analysis.recommendation.value if analysis.recommendation else None,
        "created_at": analysis.created_at.isoformat(),
        "updated_at": analysis.updated_at.isoformat(),
        "blocking": (
            {
                "reason": blocking_event.reason,
                "created_at": blocking_event.created_at.isoformat(),
            }
            if blocking_event and analysis.status == AnalysisStatus.BLOCKED
            else None
        ),
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
        "tool_runs": [
            {
                "capability": run.capability,
                "query": run.query,
                "required": run.required,
                "provider": run.provider,
                "actor_id": run.actor_id,
                "actor_build": run.actor_build,
                "status": run.status,
                "run_id": run.provider_run_id,
                "dataset_id": run.dataset_id,
                "raw_items_count": run.raw_items_count,
                "valid_items_count": run.valid_items_count,
                "observation_status": (run.parameters or {}).get("observation_status"),
                "cost_usd": run.cost_usd,
                "cost_status": (run.parameters or {}).get("cost_status", "historical_observation"),
                "cost_observed_at": (run.parameters or {}).get("cost_observed_at"),
                "cost_source": (run.parameters or {}).get("cost_source", "apify.usageTotalUsd"),
                "authorized_cap_usd": (run.parameters or {}).get("authorized_cap_usd"),
                "authorization_status": (run.parameters or {}).get("authorization_status"),
                "spending_mode": (run.parameters or {}).get("spending_mode", "legacy_caps"),
                "attempts_count": len(attempts_by_run.get(run.id, [])),
                "attempts": attempts_by_run.get(run.id, []),
                "error_code": run.error_code,
                "error_message": run.error_message,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            }
            for run in tool_runs
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
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
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

    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(400, "Header 'Idempotency-Key' é obrigatório para reanálise.")
    result = await CreateAnalysisUseCase(session, settings).execute(
        CreateAnalysisCommand(
            tenant_id=previous.tenant_id,
            course_name=previous.course_name,
            correlation_id=corr_id,
            proposal_data={
                **{
                    key: value
                    for key, value in previous.proposal_data.items()
                    if not key.startswith("_")
                },
                **payload.proposal_data,
            },
            idempotency_key=f"revision:{previous.id}:{idempotency_key.strip()}",
            previous_analysis_id=previous.id,
        )
    )
    await session.commit()
    if not result.is_existing:
        await publish_analysis_job(session, result.analysis_id, run_analysis_workflow.delay)

    return {
        "analysis_id": result.analysis_id,
        "previous_analysis_id": previous.id,
        "status": result.status.value,
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

    stmt_scr = select(ScoringResultModel).where(ScoringResultModel.analysis_id == analysis_id)
    scoring = (await session.execute(stmt_scr)).scalar_one_or_none()

    stmt_ev = select(MarketEvidenceModel).where(MarketEvidenceModel.analysis_id == analysis_id)
    evidences = list((await session.execute(stmt_ev)).scalars().all())

    stmt_an = select(AnalysisModel).where(AnalysisModel.id == analysis_id)
    analysis_row = (await session.execute(stmt_an)).scalar_one_or_none()
    proposal = dict(analysis_row.proposal_data or {}) if analysis_row else {}
    course_name = analysis_row.course_name if analysis_row else "Curso Analisado"

    area_reviews = await _load_area_reviews(session, analysis_id)

    hydrated_presentation = _hydrate_dossier_presentation(
        analysis_id=analysis_id,
        course_name=course_name,
        proposal=proposal,
        dossier=dossier,
        scoring=scoring,
        evidences=evidences,
        area_reviews=area_reviews,
    )

    return {
        "id": dossier.id,
        "analysis_id": dossier.analysis_id,
        "prompt_version": dossier.prompt_version,
        "model_name": dossier.model_name,
        "facts_hash": dossier.facts_hash,
        "status": dossier.status,
        "executive_summary": dossier.executive_summary,
        "schema_version": hydrated_presentation.get("schema_version", 1),
        "executive_summary_claim_ids": hydrated_presentation.get(
            "executive_summary_claim_ids", []
        ),
        "highlights": hydrated_presentation.get("highlights", {}),
        "limitations": hydrated_presentation.get("limitations", []),
        "analysis_audit": hydrated_presentation.get("analysis_audit", {}),
        "three_fold_review": hydrated_presentation.get("three_fold_review"),
        "presentation": hydrated_presentation,
        "sections": dossier.sections,
        "claims": dossier.claims,
        "cost_usd": dossier.cost_usd,
        "created_at": dossier.created_at.isoformat(),
        "scoring": {
            "viability_score": scoring.viability_score,
            "profile_id": scoring.profile_id,
            "partial_score": scoring.partial_score,
            "coverage_score": scoring.coverage_score,
            "confidence_score": scoring.confidence_score,
            "recommendation": scoring.recommendation,
            "pillar_scores": scoring.pillar_scores,
            "gate_details": scoring.gate_details,
            "is_experimental": scoring.is_experimental,
        }
        if scoring
        else None,
        "evidences": [
            {
                "id": ev.id,
                "evidence_type": ev.evidence_type,
                "source_name": ev.source_name,
                "source_url": ev.source_url,
                "collector": ev.collector,
                "title": ev.title,
                "sanitized_data": _public_evidence_payload(ev.sanitized_data),
                "quality_score": ev.quality_score,
                "cost_usd": ev.cost_usd,
                "collected_at": ev.collected_at.isoformat(),
            }
            for ev in evidences
        ],
    }


class SubmitDecisionRequest(BaseModel):
    """Corpo da requisição de decisão humana (RF-009)."""

    user_id: str = Field(..., description="ID do decisor institucional")
    user_role: str = Field(..., description="Papel do decisor (ex: director, coordinator)")
    decision: Literal["APPROVED", "APPROVED_WITH_ADJUSTMENTS", "REJECTED"] = Field(
        ..., description="Decisão institucional"
    )
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
    request: Request,
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
        user_id=request.state.principal.subject,
        user_role=request.state.principal.role,
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


class SubmitAreaReviewRequest(BaseModel):
    """Corpo da requisição para revisão departamental na aba Revisões do Dossiê CMS."""

    area: Literal["marketing", "produto", "comercial", "financeiro"] = Field(
        ..., description="Área responsável pela revisão"
    )
    status: Literal["APPROVED", "IN_REVIEW", "PENDING", "CHANGES_REQUESTED"] = Field(
        ..., description="Status do parecer da área"
    )
    reviewer_name: str = Field(..., min_length=2, max_length=128, description="Nome do revisor")
    comment: str = Field(default="", max_length=2000, description="Comentário ou observação da revisão")


@app.post(
    "/v1/analyses/{analysis_id}/area-reviews",
    status_code=status.HTTP_200_OK,
    summary="Registrar revisão por área no Dossiê CMS (Marketing, Produto, Comercial, Financeiro)",
)
async def submit_area_review(
    analysis_id: str,
    payload: SubmitAreaReviewRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    repo = AnalysisRepository(session)
    analysis = await repo.get_by_id(analysis_id)
    if not analysis or analysis.tenant_id != request.state.principal.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Análise não encontrada: {analysis_id}",
        )

    existing_reviews = await _load_area_reviews(session, analysis_id)
    next_version = f"v1.{len(existing_reviews) + 1}"

    review_model = DossierAreaReviewModel(
        id=f"arev_{uuid.uuid4().hex[:12]}",
        analysis_id=analysis_id,
        tenant_id=analysis.tenant_id,
        area=payload.area.lower(),
        status=payload.status.upper(),
        reviewer_name=payload.reviewer_name.strip(),
        comment=payload.comment.strip(),
        version_label=next_version,
        created_at=datetime.now(UTC),
    )
    session.add(review_model)
    await session.commit()

    all_reviews = [*existing_reviews, review_model]
    default_revisions_page = {
        "area_reviews": [
            {"area": "marketing", "label": "Marketing", "icon": "megaphone", "status": "PENDING", "status_label": "Pendente", "tone": "insufficient", "reviewer_name": "Aguardando revisão", "updated_at_label": "Disponível para parecer", "comment": ""},
            {"area": "produto", "label": "Produto", "icon": "box", "status": "PENDING", "status_label": "Pendente", "tone": "insufficient", "reviewer_name": "Aguardando revisão", "updated_at_label": "Disponível para parecer", "comment": ""},
            {"area": "comercial", "label": "Comercial", "icon": "briefcase", "status": "PENDING", "status_label": "Pendente", "tone": "insufficient", "reviewer_name": "Aguardando revisão", "updated_at_label": "Disponível para parecer", "comment": ""},
            {"area": "financeiro", "label": "Financeiro", "icon": "dollar-sign", "status": "PENDING", "status_label": "Pendente", "tone": "insufficient", "reviewer_name": "Aguardando revisão", "updated_at_label": "Disponível para parecer", "comment": ""},
        ]
    }
    updated_revisions = _apply_area_reviews_to_revisions_page(default_revisions_page, all_reviews)
    return {
        "review_id": review_model.id,
        "analysis_id": analysis_id,
        "version_label": next_version,
        **updated_revisions,
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
# ENDPOINTS DE DADOS HISTÓRICOS INSTITUCIONAIS (CRM DA IES / ENS)
# Fornece histórico de turmas, funis e métricas financeiras passadas
# para balizamento de novos cursos, calibração de quórum e comparabilidade.
# =============================================================================


@app.get("/v1/institutional/courses", summary="Listar cursos históricos da instituição")
async def list_institutional_courses(
    tenant_id: str = "ens",
    query: str | None = None,
    category: str | None = None,
    status_filter: str | None = None,
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,  # type: ignore
) -> dict[str, Any]:
    stmt = (
        select(HistoricalCourseModel)
        .where(HistoricalCourseModel.tenant_id == tenant_id)
        .order_by(HistoricalCourseModel.external_id)
    )
    if status_filter:
        stmt = stmt.where(HistoricalCourseModel.status == status_filter)
    if category:
        stmt = stmt.where(HistoricalCourseModel.category.ilike(f"%{category}%"))

    courses = (await session.execute(stmt)).scalars().all()

    # Se ainda não houver cursos no banco para o tenant, tenta carregar o dataset estático
    if not courses and tenant_id == "ens":
        from prometeus.infrastructure.institutional.ens.dataset import ENS_HISTORICAL_PORTFOLIO

        raw_items = ENS_HISTORICAL_PORTFOLIO
        if status_filter:
            raw_items = [c for c in raw_items if c["status"] == status_filter]
        if category:
            raw_items = [c for c in raw_items if category.lower() in c["category"].lower()]
        if query:
            q = query.lower()
            raw_items = [
                c
                for c in raw_items
                if q in c["name"].lower() or any(q in t.lower() for t in c["tags"])
            ]
        # Mesmo contrato de apresentação da base persistida, sem alterar as fixtures.
        raw_items = [
            {
                **item,
                "metrics_summary": {
                    "total_periods": len(item.get("funnel_history", [])),
                    "total_leads": sum(
                        row.get("leads", 0) for row in item.get("funnel_history", [])
                    ),
                    "total_enrolled": sum(
                        row.get("enrolled", 0) for row in item.get("funnel_history", [])
                    ),
                    "total_revenue_brl": round(
                        sum(
                            row.get("total_revenue_brl", 0)
                            for row in item.get("funnel_history", [])
                        ),
                        2,
                    ),
                },
            }
            for item in raw_items
        ]
        return {
            "tenant_id": tenant_id,
            "total": len(raw_items),
            "courses": raw_items,
        }

    from prometeus.infrastructure.institutional.ens.dataset import ENS_HISTORICAL_PORTFOLIO

    dataset_map = (
        {item["external_id"]: item for item in ENS_HISTORICAL_PORTFOLIO}
        if tenant_id == "ens"
        else {}
    )

    results = []
    for c in courses:
        stmt_f = select(HistoricalFunnelModel).where(HistoricalFunnelModel.course_id == c.id)
        funnels = (await session.execute(stmt_f)).scalars().all()

        total_enrolled = sum(f.enrolled for f in funnels)
        total_leads = sum(f.leads for f in funnels)
        total_revenue = sum((f.total_revenue_brl or 0.0) for f in funnels)
        avg_ticket = (
            sum((f.average_ticket_brl or 0.0) for f in funnels) / len(funnels) if funnels else 0.0
        )
        avg_conversion = (
            sum(f.conversion_lead_to_enrolled for f in funnels) / len(funnels) if funnels else 0.0
        )

        meta = dataset_map.get(c.external_id, {})
        tier = (
            meta.get("tier")
            or meta.get("performance_tier")
            or ("CANCELADO_POR_QUORUM" if c.status == "archived" else "SUCESSO")
        )
        segment = meta.get("segment") or c.category
        quorum_min = meta.get("quorum_min") or meta.get("quorum_minimum") or 18

        funnel_history: list[dict[str, Any]] = []
        for f in sorted(funnels, key=lambda x: str(x.period)):
            f_meta: dict[str, Any] = next(
                (
                    item
                    for item in meta.get("funnel_history", [])
                    if str(item.get("period")) == str(f.period)
                ),
                {},
            )
            is_cancelled = f_meta.get("status") == "CANCELLED_LOW_QUORUM" or (
                f.enrolled < quorum_min and c.status == "archived"
            )
            funnel_history.append(
                {
                    "period": str(f.period),
                    "cohort_year": str(f.period),
                    "leads": f.leads,
                    "applicants": f.applicants,
                    "enrolled": f.enrolled,
                    "ticket": f.average_ticket_brl or 0.0,
                    "average_ticket_brl": f.average_ticket_brl or 0.0,
                    "price_period": f.price_period,
                    "data_complete": f.data_complete,
                    "cohort_status": f.cohort_status,
                    "revenue": f.total_revenue_brl or 0.0,
                    "total_revenue_brl": f.total_revenue_brl or 0.0,
                    "status": "CANCELLED_LOW_QUORUM" if is_cancelled else "COMPLETED",
                    "notes": f_meta.get("notes")
                    or (
                        f"Cancelado por quórum ({f.enrolled}/{quorum_min})"
                        if is_cancelled
                        else "Turma concluída com sucesso."
                    ),
                }
            )

        course_dict = {
            "id": c.id,
            "external_id": c.external_id,
            "name": c.name,
            "category": c.category,
            "segment": segment,
            "modality": c.modality,
            "workload_hours": c.workload_hours,
            "status": c.status,
            "tier": tier,
            "quorum_min": quorum_min,
            "tags": c.tags or [],
            "target_audience": c.target_audience or [],
            "family": c.family,
            "curriculum_text": c.curriculum_text,
            "curriculum_modules": c.curriculum_modules or [],
            "is_synthetic": meta.get("is_synthetic", False),
            "dataset_version": meta.get("dataset_version"),
            "academic_reference": meta.get("academic_reference"),
            "curriculum_origin": meta.get("curriculum_origin"),
            "funnel_origin": meta.get("funnel_origin"),
            "price_origin": meta.get("price_origin"),
            "metrics_summary": {
                "total_periods": len(funnels),
                "total_leads": total_leads,
                "total_enrolled": total_enrolled,
                "average_ticket_brl": round(avg_ticket, 2),
                "total_revenue_brl": round(total_revenue, 2),
                "avg_conversion_rate": round(avg_conversion, 4),
            },
            "funnel_history": funnel_history,
        }

        if query:
            q = query.lower()
            name_match = q in c.name.lower()
            tag_match = any(q in t.lower() for t in (c.tags or []))
            if not (name_match or tag_match):
                continue

        results.append(course_dict)

    return {
        "tenant_id": tenant_id,
        "total": len(results),
        "courses": results,
    }


@app.get(
    "/v1/institutional/courses/{external_id}",
    summary="Obter detalhes e funil de curso histórico",
)
async def get_institutional_course_detail(
    external_id: str,
    tenant_id: str = "ens",
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,  # type: ignore
) -> dict[str, Any]:
    stmt = select(HistoricalCourseModel).where(
        HistoricalCourseModel.tenant_id == tenant_id,
        HistoricalCourseModel.external_id == external_id,
    )
    course = (await session.execute(stmt)).scalar_one_or_none()
    if not course:
        from prometeus.infrastructure.institutional.ens.dataset import ENS_HISTORICAL_PORTFOLIO

        found = next((c for c in ENS_HISTORICAL_PORTFOLIO if c["external_id"] == external_id), None)
        if found and tenant_id == "ens":
            return found
        raise HTTPException(
            status_code=404, detail=f"Curso histórico '{external_id}' não encontrado."
        )

    stmt_f = (
        select(HistoricalFunnelModel)
        .where(HistoricalFunnelModel.course_id == course.id)
        .order_by(HistoricalFunnelModel.period)
    )
    funnels = (await session.execute(stmt_f)).scalars().all()

    from prometeus.infrastructure.institutional.ens.dataset import ENS_HISTORICAL_PORTFOLIO

    meta = (
        next((c for c in ENS_HISTORICAL_PORTFOLIO if c["external_id"] == external_id), {})
        if tenant_id == "ens"
        else {}
    )

    return {
        "id": course.id,
        "external_id": course.external_id,
        "name": course.name,
        "category": course.category,
        "modality": course.modality,
        "workload_hours": course.workload_hours,
        "status": course.status,
        "tags": course.tags or [],
        "target_audience": course.target_audience or [],
        "family": course.family,
        "curriculum_text": course.curriculum_text,
        "curriculum_modules": course.curriculum_modules or [],
        "is_synthetic": meta.get("is_synthetic", False),
        "dataset_version": meta.get("dataset_version"),
        "academic_reference": meta.get("academic_reference"),
        "curriculum_origin": meta.get("curriculum_origin"),
        "funnel_origin": meta.get("funnel_origin"),
        "price_origin": meta.get("price_origin"),
        "funnel_history": [
            {
                "period": f.period,
                "leads": f.leads,
                "applicants": f.applicants,
                "enrolled": f.enrolled,
                "conversion_lead_to_applicant": f.conversion_lead_to_applicant,
                "conversion_applicant_to_enrolled": f.conversion_applicant_to_enrolled,
                "conversion_lead_to_enrolled": f.conversion_lead_to_enrolled,
                "average_ticket_brl": f.average_ticket_brl,
                "price_period": f.price_period,
                "data_complete": f.data_complete,
                "cohort_status": f.cohort_status,
                "total_revenue_brl": f.total_revenue_brl,
            }
            for f in funnels
        ],
    }


@app.post("/v1/institutional/seed", summary="Semear ou sincronizar base histórica no PostgreSQL")
async def seed_institutional_data_endpoint(
    tenant_id: str = "ens",
    reset: bool = False,
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,  # type: ignore
) -> dict[str, Any]:
    from prometeus.infrastructure.institutional.ens.seeder import seed_historical_courses

    stats = await seed_historical_courses(session, tenant_id=tenant_id, reset=reset)
    return {
        "status": "SUCCESS",
        "message": f"Base histórica do tenant '{tenant_id}' sincronizada com sucesso.",
        "stats": stats,
    }


# =============================================================================
# ENDPOINTS DE CONFIGURAÇÃO DE IA E INTEGRAÇÕES VIA APP (UI-FIRST)
# Permite que o usuário configure Provedores, Modelos, Raciocínio e Scrapers
# diretamente pela interface web sem necessidade de acesso manual a arquivos .env.
# =============================================================================


class SettingsUpdateRequest(BaseModel):
    gen_llm_provider: str | None = None
    gen_llm_model: str | None = None
    gen_llm_reasoning_effort: str | None = None
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    typesafe_api_key: str | None = None
    jev_model: str | None = None
    apify_token: str | None = None
    apify_max_charge: float | None = None
    apify_discovery_mcp_enabled: bool | None = None


def _env_path() -> Path:
    local_path = Path(".env")
    return local_path if local_path.exists() or not Path("/app").is_dir() else Path("/app/.env")


def _persist_env_updates(updates: dict[str, str]) -> None:
    """Atualiza somente chaves conhecidas sem permitir injeção de novas linhas."""
    if any("\n" in value or "\r" in value for value in updates.values()):
        raise HTTPException(status_code=422, detail="Valor de configuração inválido.")
    env_path = _env_path()
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    new_lines: list[str] = []
    found_keys: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}")
                found_keys.add(key)
                continue
        new_lines.append(line)
    for key, value in updates.items():
        if key not in found_keys:
            new_lines.append(f"{key}={value}")
    content = "\n".join(new_lines) + "\n"
    written = False
    temporary: Path | None = None
    try:
        temporary = env_path.with_suffix(f".tmp.{os.getpid()}")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(env_path)
        written = True
    except OSError:
        pass
    finally:
        if not written and temporary is not None and temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass

    if not written:
        try:
            env_path.write_text(content, encoding="utf-8")
        except OSError as exc:
            logger.warning("Falha ao gravar arquivo de configuração %s: %s", env_path, exc)
            raise HTTPException(
                status_code=500, detail="Não foi possível persistir a configuração."
            ) from exc
    os.environ.update(updates)


@app.get("/v1/settings", summary="Obter configurações ativas de IA e conectores")
async def get_settings() -> dict[str, Any]:
    settings = AppSettings()
    runtime = validate_runtime_preflight(settings)
    oauth_credentials = ChatGPTCredentialStore(settings.CHATGPT_CREDENTIALS_PATH).load()

    def mask(val: str) -> str:
        if not val or not val.strip():
            return ""
        if len(val) <= 8:
            return "••••••••"
        return f"{val[:4]}••••••••{val[-4:]}"

    return {
        "gen_llm_provider": settings.GEN_LLM_PROVIDER,
        "gen_llm_model": (
            oauth_credentials.selected_model
            if oauth_credentials and settings.GEN_LLM_PROVIDER in {"chatgpt_oauth", "codex"}
            else settings.GEN_LLM_MODEL
        ),
        "gen_llm_reasoning_effort": settings.GEN_LLM_REASONING_EFFORT or "",
        "chatgpt_access_token_masked": mask(settings.CHATGPT_ACCESS_TOKEN),
        "chatgpt_oauth_connected": bool(oauth_credentials and oauth_credentials.has_direct_usage),
        "chatgpt_oauth_email": oauth_credentials.email if oauth_credentials else None,
        "chatgpt_oauth_model": oauth_credentials.selected_model if oauth_credentials else None,
        "openai_api_key_masked": mask(settings.OPENAI_API_KEY),
        "typesafe_api_key_masked": mask(settings.TYPESAFE_API_KEY),
        "jev_model": settings.JEV_MODEL,
        "is_jev_configured": settings.is_jev_configured,
        "is_traditional_llm_configured": settings.is_traditional_llm_configured,
        "ai_mode": runtime.ai_mode,
        "jev_enabled": runtime.jev_enabled,
        "mode": (
            "HYBRID (JEV System One + LLM Tradicional)"
            if runtime.jev_enabled
            else "100% TRADITIONAL (LLM assume decisões e textos)"
        ),
        "apify_token_masked": mask(settings.APIFY_TOKEN),
        "apify_max_charge": None,
        "apify_spending_mode": "monitor_only",
        "apify_legacy_max_charge": settings.APIFY_MAX_TOTAL_CHARGE_USD_PER_ANALYSIS,
        "apify_discovery_mcp_enabled": settings.APIFY_DISCOVERY_MCP_ENABLED,
    }


@app.post("/v1/settings", summary="Atualizar configurações de IA e conectores via app")
async def update_settings_endpoint(payload: SettingsUpdateRequest) -> dict[str, Any]:
    if payload.apify_max_charge is not None:
        raise HTTPException(
            status_code=422,
            detail="Novas análises usam monitoramento de custos, sem teto monetário por chamada. Atualize a tela de configurações.",
        )
    settings = AppSettings()
    provider = payload.gen_llm_provider or settings.GEN_LLM_PROVIDER
    if payload.gen_llm_provider is not None and provider not in {
        "openai",
        "openrouter",
        "chatgpt_oauth",
    }:
        raise HTTPException(status_code=422, detail="Provedor de LLM não suportado.")
    selected_credentials: ChatGPTCredentials | None = None
    model = payload.gen_llm_model.strip() if payload.gen_llm_model is not None else None
    effort = payload.gen_llm_reasoning_effort
    if effort is not None and effort not in REASONING_EFFORTS and effort != "":
        raise HTTPException(status_code=422, detail="Nível de raciocínio não suportado.")
    if model is not None and not model:
        raise HTTPException(status_code=422, detail="Selecione um modelo válido.")
    if provider in {"chatgpt_oauth", "codex"} and (model is not None or effort is not None):
        selected_credentials, catalog = await _chatgpt_account_catalog(settings)
        model = model or selected_credentials.selected_model
        selected = next((item for item in catalog if item["slug"] == model), None)
        if selected is None:
            raise HTTPException(
                status_code=422,
                detail="O modelo selecionado não está disponível nesta conta ChatGPT. Atualize a lista de modelos.",
            )
        effective_effort = effort if effort is not None else settings.GEN_LLM_REASONING_EFFORT
        supported = selected.get("supported_reasoning_efforts")
        if effective_effort and isinstance(supported, list) and effective_effort not in supported:
            raise HTTPException(
                status_code=422,
                detail="O nível de raciocínio selecionado não é suportado por este modelo.",
            )
    updates: dict[str, str] = {}
    if payload.gen_llm_provider is not None:
        if payload.gen_llm_provider not in {"openai", "openrouter", "chatgpt_oauth"}:
            raise HTTPException(status_code=422, detail="Provedor de LLM não suportado.")
        updates["GEN_LLM_PROVIDER"] = payload.gen_llm_provider
    if model is not None:
        updates["GEN_LLM_MODEL"] = model
    if payload.gen_llm_reasoning_effort is not None:
        updates["GEN_LLM_REASONING_EFFORT"] = payload.gen_llm_reasoning_effort
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
    if payload.apify_discovery_mcp_enabled is not None:
        updates["APIFY_DISCOVERY_MCP_ENABLED"] = str(payload.apify_discovery_mcp_enabled).lower()

    previous_credentials: ChatGPTCredentials | None = None
    credential_store = ChatGPTCredentialStore(settings.CHATGPT_CREDENTIALS_PATH)
    if selected_credentials is not None and model is not None:
        try:
            previous_credentials = credential_store.select_model(
                model, expected_subject=selected_credentials.subject
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from None
    try:
        _persist_env_updates(updates)
    except Exception:
        if previous_credentials is not None:
            credential_store.restore_model_selection(
                previous_credentials, failed_selection=str(model)
            )
        raise
    logger.info("Configurações atualizadas com sucesso via REST API /v1/settings.")
    return {"status": "SUCCESS", "message": "Configurações salvas com sucesso no Prometeus."}


# =============================================================================
# FLUXO OAUTH 1-CLIQUE: CHATGPT & CODEX (BASEADO EM PROMETEUS-AION)
# Utiliza o protocolo oficial PKCE S256 com Client ID app_EMoamEEZ73f0CkXaXp7hrann
# e suporte a autorização oficial OpenAI e simulação rápida em staging.
# =============================================================================

_chatgpt_catalog_lock = asyncio.Lock()


class ApifyDiscoveryRequest(BaseModel):
    tool: Literal["search-actors", "fetch-actor-details", "search-apify-docs", "fetch-apify-docs"]
    arguments: dict[str, Any] = Field(default_factory=dict)


@app.post("/v1/settings/apify/discovery", summary="Consultar catálogo e documentação Apify sem executar Actors")
async def apify_discovery_lookup(payload: ApifyDiscoveryRequest) -> dict[str, Any]:
    from prometeus.infrastructure.apify.discovery_mcp import ApifyDiscoveryMCP

    settings = AppSettings()
    result = await ApifyDiscoveryMCP(enabled=settings.APIFY_DISCOVERY_MCP_ENABLED).lookup(
        payload.tool, payload.arguments,
    )
    return result.model_dump(mode="json")


async def _chatgpt_account_catalog(
    settings: AppSettings,
) -> tuple[ChatGPTCredentials, list[dict[str, Any]]]:
    async with _chatgpt_catalog_lock:
        store = ChatGPTCredentialStore(settings.CHATGPT_CREDENTIALS_PATH)
        credentials = store.load()
        if credentials is None or not credentials.has_direct_usage:
            raise HTTPException(
                status_code=401,
                detail="Conecte sua conta ChatGPT para consultar os modelos disponíveis.",
            )
        if credentials.expires_at <= time.time() + 60:
            try:
                credentials = await refresh_chatgpt_tokens(credentials)
                store.save(credentials)
            except Exception as exc:
                logger.warning("Falha ao renovar sessão ChatGPT: %s", type(exc).__name__)
                raise HTTPException(
                    status_code=502,
                    detail="Não foi possível renovar a sessão ChatGPT. Tente atualizar a lista novamente.",
                ) from None
        try:
            catalog = await list_chatgpt_models(credentials.access_token)
            models = [
                public_chatgpt_model(item)
                for item in catalog
                if isinstance(item, dict) and item.get("slug")
            ]
        except Exception as exc:
            logger.warning("Falha ao consultar catálogo ChatGPT: %s", type(exc).__name__)
            raise HTTPException(
                status_code=502,
                detail="Não foi possível consultar os modelos da conta ChatGPT. Tente atualizar a lista novamente.",
            ) from None
        if not models:
            raise HTTPException(
                status_code=502,
                detail="A conta ChatGPT não retornou modelos disponíveis. Tente atualizar a lista novamente.",
            )
        return credentials, models


@app.get("/v1/auth/chatgpt/models", summary="Listar modelos disponíveis na conta ChatGPT conectada")
async def chatgpt_oauth_models() -> dict[str, Any]:
    credentials, models = await _chatgpt_account_catalog(AppSettings())
    return {"models": models, "selected_model": credentials.selected_model}


@app.get("/v1/auth/chatgpt/url", summary="Obter URL oficial de autorização da OpenAI com PKCE")
async def chatgpt_oauth_url() -> dict[str, str]:
    """Gera o par PKCE S256 e retorna a URL oficial da OpenAI para o fluxo OAuth direto."""
    settings = AppSettings()
    credentials = ChatGPTCredentialStore(settings.CHATGPT_CREDENTIALS_PATH).load()
    auth_data = build_chatgpt_auth_url(
        client_id=credentials.client_id if credentials else DYNAMIC_CLIENT_ID
    )
    return {
        "auth_url": auth_data["auth_url"],
        "state": auth_data["state"],
        "redirect_uri": auth_data["redirect_uri"],
    }


@app.get(
    "/v1/auth/chatgpt/login",
    summary="Redirecionar diretamente para tela oficial de login da OpenAI",
)
async def chatgpt_oauth_login() -> RedirectResponse:
    """Redireciona o navegador diretamente para a tela oficial de login da OpenAI com PKCE."""
    settings = AppSettings()
    credentials = ChatGPTCredentialStore(settings.CHATGPT_CREDENTIALS_PATH).load()
    auth_data = build_chatgpt_auth_url(
        client_id=credentials.client_id if credentials else DYNAMIC_CLIENT_ID
    )
    return RedirectResponse(
        url=auth_data["auth_url"], status_code=status.HTTP_307_TEMPORARY_REDIRECT
    )


@app.get("/v1/auth/chatgpt/consent", summary="Redirecionar para o consentimento oficial")
async def chatgpt_oauth_consent() -> RedirectResponse:
    settings = AppSettings()
    credentials = ChatGPTCredentialStore(settings.CHATGPT_CREDENTIALS_PATH).load()
    auth_data = build_chatgpt_auth_url(
        client_id=credentials.client_id if credentials else DYNAMIC_CLIENT_ID
    )
    return RedirectResponse(
        url=auth_data["auth_url"], status_code=status.HTTP_307_TEMPORARY_REDIRECT
    )


@app.get(
    "/auth/callback",
    response_class=HTMLResponse,
    summary="Callback padrão OpenAI Codex na porta 1455",
)
@app.get(
    "/v1/auth/chatgpt/callback",
    response_class=HTMLResponse,
    summary="Callback de redirecionamento OAuth do ChatGPT",
)
async def chatgpt_oauth_callback(
    code: str = "",
    state: str = "",
    error: str = "",
    client_id: str = "",
) -> str:
    """Troca e valida a autorização oficial antes de ativar a conta."""
    verifier_entry = get_verifier_for_state(state)
    if not verifier_entry:
        return """<!DOCTYPE html><html><body><h3>Estado OAuth expirado ou já utilizado.</h3>
        <script>setTimeout(() => window.close(), 3000);</script>
        </body></html>"""
    if error:
        return f"""<!DOCTYPE html><html><body><h3>Autorização não concluída: {html.escape(error)}</h3>
        <script>setTimeout(() => window.close(), 3000);</script></body></html>"""
    if not code:
        return """<!DOCTYPE html><html><body><h3>O callback não recebeu código OAuth.</h3>
        <script>setTimeout(() => window.close(), 3000);</script></body></html>"""

    if verifier_entry.requested_client_id == DYNAMIC_CLIENT_ID:
        effective_client_id = client_id
        if not effective_client_id.startswith("oaiapp_"):
            return """<!DOCTYPE html><html><body><h3>Registro OAuth não retornou client_id válido.</h3>
            <script>setTimeout(() => window.close(), 3000);</script></body></html>"""
    else:
        effective_client_id = verifier_entry.requested_client_id
        if client_id and client_id != effective_client_id:
            return """<!DOCTYPE html><html><body><h3>client_id divergente; autorização rejeitada.</h3>
            <script>setTimeout(() => window.close(), 3000);</script></body></html>"""

    try:
        token_result = await exchange_chatgpt_code(
            code=code,
            code_verifier=verifier_entry.code_verifier,
            client_id=effective_client_id,
            nonce=verifier_entry.nonce,
            redirect_uri=verifier_entry.redirect_uri,
        )
        models = await list_chatgpt_models(token_result.access_token)
        if not models:
            raise RuntimeError("A conta não retornou modelos disponíveis para uso direto.")
        configured_model = AppSettings().GEN_LLM_MODEL
        available_slugs = [model["slug"] for model in models]
        selected_model = (
            configured_model if configured_model in available_slugs else available_slugs[0]
        )
        validation_client = ChatGPTPlanGenerativeClient(
            access_token=token_result.access_token,
            model=selected_model,
            reasoning_effort="none",
        )
        validation_text = await validation_client.generate_text(
            "Responda exatamente: OAuth Prometeus validado."
        )
        if not validation_text.strip():
            raise RuntimeError("A inferência de validação terminou sem conteúdo.")

        settings = AppSettings()
        credentials = ChatGPTCredentials(
            access_token=token_result.access_token,
            refresh_token=token_result.refresh_token,
            id_token=token_result.id_token,
            expires_at=time.time() + token_result.expires_in,
            scopes=token_result.scopes,
            client_id=token_result.client_id,
            subject=token_result.subject,
            email=token_result.email,
            selected_model=selected_model,
        )
        ChatGPTCredentialStore(settings.CHATGPT_CREDENTIALS_PATH).save(credentials)
        try:
            _persist_env_updates(
                {
                    "GEN_LLM_PROVIDER": "chatgpt_oauth",
                    "GEN_LLM_MODEL": selected_model,
                    "CHATGPT_ACCESS_TOKEN": "",
                }
            )
        except Exception as exc:
            logger.warning("Credenciais salvas, mas falha ao atualizar .env: %s", exc)
        message = json.dumps({"type": "CHATGPT_OAUTH_SUCCESS"})
        return f"""<!DOCTYPE html><html><body><h2>Conexão validada com sucesso</h2>
        <p>{html.escape(token_result.email or "Conta ChatGPT")}</p>
        <p>Modelo validado: {html.escape(selected_model)}</p>
        <script>if(window.opener)window.opener.postMessage({message}, window.location.origin);
        setTimeout(() => window.close(), 1200);</script></body></html>"""
    except Exception as exc:
        logger.exception("Falha ao validar a conexão ChatGPT OAuth.")
        return f"""<!DOCTYPE html><html><body><h3>Falha ao validar ChatGPT OAuth</h3>
        <p>{html.escape(str(exc))}</p><script>setTimeout(() => window.close(), 5000);</script>
        </body></html>"""


@app.post("/v1/auth/chatgpt/authorize", summary="Processar autorização OAuth 1-clique")
async def chatgpt_oauth_authorize() -> dict[str, Any]:
    """Impossível simular autorização: somente o callback oficial pode conectar."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Fluxo simulado removido. Use /v1/auth/chatgpt/login.",
    )


@app.post("/v1/auth/chatgpt/disconnect", summary="Desconectar conta ChatGPT OAuth")
async def chatgpt_oauth_disconnect() -> dict[str, Any]:
    """Remove localmente o conjunto completo de credenciais OAuth."""
    settings = AppSettings()
    ChatGPTCredentialStore(settings.CHATGPT_CREDENTIALS_PATH).clear()
    _persist_env_updates({"CHATGPT_ACCESS_TOKEN": ""})
    logger.info("Credenciais locais ChatGPT OAuth removidas.")
    return {"status": "DISCONNECTED", "remote_revocation_confirmed": False}


@app.get("/v1/auth/chatgpt/status", summary="Consultar status da conexão ChatGPT OAuth")
async def chatgpt_oauth_status() -> dict[str, Any]:
    settings = AppSettings()
    credentials = ChatGPTCredentialStore(settings.CHATGPT_CREDENTIALS_PATH).load()
    is_connected = bool(credentials and credentials.has_direct_usage)
    return {
        "connected": is_connected,
        "provider": settings.GEN_LLM_PROVIDER,
        "model": credentials.selected_model if credentials else None,
        "reasoning_effort": settings.GEN_LLM_REASONING_EFFORT,
        "email": credentials.email if credentials else None,
        "direct_usage_scope": bool(credentials and DIRECT_USAGE_SCOPE in credentials.scopes),
        "expires_at": credentials.expires_at if credentials else None,
    }


# =============================================================================
_TENANT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,62}$")


def _load_tenant_config_by_id(tenant_id: str, settings: AppSettings) -> TenantConfig:
    """Resolve a configuração pública do tenant sem expor caminhos fora de config/tenants."""
    try:
        return resolve_tenant_config_for_id(tenant_id, settings, allow_synthetic_fallback=False)
    except TenantNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' não encontrado.",
        ) from exc
    except ConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Configuração inválida para o tenant '{tenant_id}': {exc}",
        ) from exc


class SectorRadarRefreshRequest(BaseModel):
    force: bool = False
    max_budget_usd: float = Field(default=1.50, gt=0.0, le=10.0)


@app.get(
    "/v1/tenants/{tenant_id}/ecosystem",
    summary="Consultar concorrentes fixos e Radar Setorial Permanente do tenant",
)
async def get_tenant_ecosystem(
    tenant_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    settings = AppSettings()
    cfg = _load_tenant_config_by_id(tenant_id, settings)
    radar_service = SectorRadarService(session=session)
    latest = await radar_service.get_latest_snapshot(cfg.institution.id, include_expired=True)
    serialized_radar = serialize_radar_snapshot(latest)
    if serialized_radar is None:
        radar_status: dict[str, Any] = {
            "has_snapshot": False,
            "is_fresh": False,
            "status": "EMPTY",
            "collected_at": None,
            "expires_at": None,
            "signals_count": 0,
            "covered_actors": [],
            "trending_themes": [],
        }
    else:
        radar_status = {
            "has_snapshot": True,
            "is_fresh": serialized_radar["is_fresh"],
            "status": serialized_radar["status"],
            "collected_at": serialized_radar["collected_at"],
            "expires_at": serialized_radar["expires_at"],
            "signals_count": serialized_radar["signals_count"],
            "covered_actors": serialized_radar["covered_actors"],
            "trending_themes": serialized_radar["trending_themes"],
        }

    return {
        "tenant_id": cfg.institution.id,
        "institution_name": cfg.institution.display_name,
        "allow_extra_intake_competitors": cfg.ecosystem.allow_extra_intake_competitors,
        "radar_ttl_hours": cfg.ecosystem.radar_ttl_hours,
        "competitors": [c.model_dump(mode="json") for c in cfg.ecosystem.competitors],
        "sector_radar": [s.model_dump(mode="json") for s in cfg.ecosystem.sector_radar],
        "radar_status": radar_status,
    }


@app.post(
    "/v1/tenants/{tenant_id}/sector-radar/refresh",
    summary="Atualizar snapshot do Radar Setorial Permanente",
)
async def refresh_tenant_sector_radar(
    tenant_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    payload: SectorRadarRefreshRequest | None = None,
) -> dict[str, Any]:
    from prometeus.infrastructure.apify.client import ApifyClient
    from prometeus.infrastructure.apify.registry import ActorConfigurationError, ApifyActorRegistry

    req = payload or SectorRadarRefreshRequest()
    settings = AppSettings()
    if settings.KILL_SWITCH_ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kill switch operacional ativo: atualização externa do Radar Setorial suspensa temporariamente.",
        )
    cfg = _load_tenant_config_by_id(tenant_id, settings)
    if not cfg.ecosystem.sector_radar:
        return {
            "tenant_id": cfg.institution.id,
            "snapshot_id": None,
            "status": "NOT_CONFIGURED",
            "collected_at": None,
            "expires_at": None,
            "signals_count": 0,
            "covered_actors": [],
            "trending_themes": [],
            "spent_usd": 0.0,
        }

    executor = None
    allowed_caps: list[str] | None = None
    if settings.APIFY_TOKEN.strip():
        try:
            registry = ApifyActorRegistry.from_settings(settings)
            allowed_caps = list(registry.capabilities)
            if allowed_caps:
                executor = ApifyClient(
                    api_token=settings.APIFY_TOKEN,
                    registry=registry,
                    base_url=settings.APIFY_BASE_URL,
                    timeout_seconds=float(settings.GEN_LLM_TIMEOUT_SECONDS),
                )
        except ActorConfigurationError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc

    service = SectorRadarService(
        session=session,
        executor=executor,
        allowed_capabilities=allowed_caps,
    )
    try:
        snapshot = await service.refresh_radar(
            tenant_id=cfg.institution.id,
            tenant_config=cfg,
            max_budget_usd=req.max_budget_usd,
            force=req.force,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    serialized = serialize_radar_snapshot(snapshot) or {}
    return {
        "tenant_id": cfg.institution.id,
        "snapshot_id": serialized.get("id"),
        "status": serialized.get("status", snapshot.status),
        "collected_at": serialized.get("collected_at"),
        "expires_at": serialized.get("expires_at"),
        "signals_count": serialized.get("signals_count", 0),
        "covered_actors": serialized.get("covered_actors", []),
        "trending_themes": serialized.get("trending_themes", []),
        "spent_usd": serialized.get("spent_usd", 0.0),
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
