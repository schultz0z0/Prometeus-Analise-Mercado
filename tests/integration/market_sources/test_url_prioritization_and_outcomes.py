"""Testes de integração para priorização de URLs e registro explícito de outcomes.

Valida requisitos da Tarefa 2.3 do plano de inteligência de mercado:
- Priorização determinística de URLs descobertas: curso > catálogo > documento/PDF > notícia
- Diversidade de domínio (máximo 2 URLs por domínio para evitar monopolização)
- Eliminação de URLs malformadas antes de gastar cota
- Confirmação de páginas usando maxCrawlDepth=0
- Cada URL recebe outcome explícito (fetched, not_found, blocked, unsupported_type, budget_skipped, extraction_failed)
- 404 JAMAIS se torna oferta válida no banco
- Tratamento de PDF com MIME, trechos e data observada
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.collect_market_evidence import CollectMarketEvidenceService
from prometeus.domain.analyses import Analysis
from prometeus.domain.configuration import AppSettings
from prometeus.domain.research import CourseResearchPlan, PlannedToolCall
from prometeus.infrastructure.apify.registry import ApifyActorRegistry
from prometeus.infrastructure.apify.schemas import ApifyExecutionResult, ApifyRunMetadata
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base, MarketEvidenceModel, ToolRunModel


def make_registry():
    return ApifyActorRegistry.from_settings(
        AppSettings(
            _env_file=None,
            APIFY_ACTOR_GOOGLE_SEARCH="apify/google-search-scraper@0.0.474",
            APIFY_ACTOR_WEB_CRAWLER="apify/website-content-crawler@0.3.102",
        )
    )


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        analysis = Analysis.create(tenant_id="ens", course_name="MBA", correlation_id="test-urls")
        analysis.id = "analysis-urls"
        await AnalysisRepository(db).save(analysis)
        await db.commit()
        yield db
    await engine.dispose()


@dataclass
class UrlMockExecutor:
    payloads: dict[str, list[dict]]
    calls: list[PlannedToolCall] = field(default_factory=list)

    async def execute(self, planned: PlannedToolCall, *, max_total_charge_usd: float) -> ApifyExecutionResult:
        self.calls.append(planned)
        registry = make_registry()
        spec = registry.require(planned.capability)
        items = self.payloads.get(planned.id, [])
        return ApifyExecutionResult(
            run=ApifyRunMetadata(
                run_id=f"run-{planned.id}",
                dataset_id=f"ds-{planned.id}",
                status="SUCCEEDED",
                actor_id=spec.actor_id,
                build_number=spec.build,
                cost_usd=0.03,
            ),
            items=items,
            total_items=len(items),
        )


def test_malformed_urls_are_rejected_before_crawl():
    # Example of malformed URL from Call 16 in the audit:
    malformed = "https://securitariosp.org.br/curso/www.securitariosp.org.br"
    assert CollectMarketEvidenceService._is_usable_discovered_url("web_crawler", malformed) is False

    valid = "https://www.pucsp.br/pos-graduacao/mba-gestao-de-riscos-e-fraudes"
    assert CollectMarketEvidenceService._is_usable_discovered_url("web_crawler", valid) is True


def test_url_prioritization_and_domain_diversity():
    urls = [
        # Domain 1: 3 URLs (should cap at 2)
        "https://fgv.br/cursos/mba-fraudes-1",
        "https://fgv.br/cursos/mba-fraudes-2",
        "https://fgv.br/cursos/mba-fraudes-3",
        # PDF URL
        "https://swissre.com/dam/treinamento_antifraude.2021.pdf",
        # Generic news article
        "https://noticias.uol.com.br/artigo-geral.html",
        # Domain 2: course URL
        "https://pucsp.br/pos/mba-fraudes",
    ]

    prioritized = CollectMarketEvidenceService._prioritize_crawler_urls(
        urls, query="mba fraudes seguros", max_urls=4
    )

    # Should retain exactly 4 URLs
    assert len(prioritized) == 4
    # FGV domain has max 2 URLs (domain diversity enforced)
    fgv_urls = [u for u in prioritized if "fgv.br" in u]
    assert len(fgv_urls) <= 2
    # Specific course URLs (FGV, PUC) take priority over generic news
    assert "https://noticias.uol.com.br/artigo-geral.html" not in prioritized[:2]


def test_404_not_found_is_rejected_and_never_becomes_valid_offer():
    call = PlannedToolCall(
        id="call-crawl-404",
        capability="web_crawler",
        query="curso",
        rationale="teste 404",
        required=False,
        max_items=5,
        parameters={"urls": ["https://exemplo.com.br/curso-inexistente"]},
    )
    # 404 item returned by scraper
    not_found_item = {
        "url": "https://exemplo.com.br/curso-inexistente",
        "httpStatusCode": 404,
        "title": "404 - Página não encontrada",
        "text": "Desculpe, a página que você procura não foi encontrada.",
    }
    result = ApifyExecutionResult(
        run=ApifyRunMetadata(
            run_id="run-404",
            dataset_id="ds-404",
            status="SUCCEEDED",
            actor_id="apify/website-content-crawler",
            build_number="0.3.102",
            cost_usd=0.01,
        ),
        items=[not_found_item],
        total_items=1,
    )

    retained, rejected = CollectMarketEvidenceService._normalized_items(call, result)
    assert len(retained) == 0
    assert len(rejected) == 1
    assert rejected[0]["reason"] in {"page_not_found", "http_404", "not_found"}


@pytest.mark.asyncio
async def test_crawler_page_confirmation_sets_max_crawl_depth_zero(session):
    registry = make_registry()
    discovery_call = PlannedToolCall(
        id="call-disc-depth",
        capability="google_search",
        query="mba fraudes",
        rationale="descobrir",
        required=False,
        max_items=3,
        parameters={},
    )
    crawl_call = PlannedToolCall(
        id="call-crawl-depth",
        capability="web_crawler",
        query="mba fraudes",
        rationale="confirmar paginas especificas",
        required=False,
        max_items=3,
        parameters={"depends_on": ["call-disc-depth"]},
    )
    plan = CourseResearchPlan(
        id="plan-depth-test",
        analysis_id="analysis-urls",
        tenant_id="ens",
        understanding_summary="fraudes",
        understanding_hash="hash-depth",
        tool_calls=[discovery_call, crawl_call],
        budget_limit_usd=1.0,
    )

    discovered_url = "https://pucsp.br/pos/mba-fraudes"
    disc_items = [
        {"url": "https://google.com/search", "organicResults": [{"url": discovered_url, "title": "MBA Fraudes PUC"}]}
    ]
    crawl_items = [
        {"url": discovered_url, "httpStatusCode": 200, "title": "MBA em Fraudes", "text": "Conteúdo do curso..."}
    ]
    executor = UrlMockExecutor(payloads={"call-disc-depth": disc_items, "call-crawl-depth": crawl_items})

    service = CollectMarketEvidenceService(
        session=session,
        executor=executor,
        registry=registry,
    )

    await service.collect(tenant_id="ens", plan=plan)

    # Check that crawl_call was executed with maxCrawlDepth=0 in its effective actor input
    executed_crawl = [c for c in executor.calls if c.id == "call-crawl-depth"][0]
    actor_input = registry.build_input(executed_crawl)
    assert actor_input.get("maxCrawlDepth") == 0


@pytest.mark.asyncio
async def test_audit_records_explicit_outcome_per_url(session):
    registry = make_registry()
    discovery_call = PlannedToolCall(
        id="call-disc-outcomes",
        capability="google_search",
        query="fraudes",
        rationale="descobrir",
        required=False,
        max_items=3,
        parameters={},
    )
    crawl_call = PlannedToolCall(
        id="call-crawl-outcomes",
        capability="web_crawler",
        query="fraudes",
        rationale="confirmar",
        required=False,
        max_items=2,
        parameters={"depends_on": ["call-disc-outcomes"]},
    )
    plan = CourseResearchPlan(
        id="plan-outcomes-test",
        analysis_id="analysis-urls",
        tenant_id="ens",
        understanding_summary="fraudes",
        understanding_hash="hash-outcomes",
        tool_calls=[discovery_call, crawl_call],
        budget_limit_usd=1.0,
    )

    url_success = "https://escola1.com.br/curso"
    url_404 = "https://escola2.com.br/inexistente"

    disc_items = [
        {"url": "https://google.com", "organicResults": [{"url": url_success, "title": "Curso 1"}, {"url": url_404, "title": "Curso 2"}]}
    ]
    crawl_items = [
        {"url": url_success, "httpStatusCode": 200, "title": "Curso Válido", "text": "Detalhes"},
        {"url": url_404, "httpStatusCode": 404, "title": "Página não encontrada", "text": "404 Not Found"},
    ]
    executor = UrlMockExecutor(payloads={"call-disc-outcomes": disc_items, "call-crawl-outcomes": crawl_items})

    service = CollectMarketEvidenceService(
        session=session,
        executor=executor,
        registry=registry,
    )

    await service.collect(tenant_id="ens", plan=plan)

    run_row = (
        await session.execute(
            select(ToolRunModel).where(
                ToolRunModel.research_plan_id == plan.id,
                ToolRunModel.planned_call_id == "call-crawl-outcomes",
            )
        )
    ).scalar_one()

    audit = run_row.parameters
    assert "url_outcomes" in audit
    outcomes = audit["url_outcomes"]
    assert outcomes[url_success] == "fetched"
    assert outcomes[url_404] == "not_found"


@pytest.mark.asyncio
async def test_pdf_prioritized_has_explicit_outcome_and_mime_tracking(session):
    registry = make_registry()
    pdf_url = "https://swissre.com/dam/treinamento_antifraude.2021.pdf"
    discovery_call = PlannedToolCall(
        id="call-disc-pdf",
        capability="google_search",
        query="treinamento antifraude pdf",
        rationale="descobrir pdf",
        required=False,
        max_items=3,
        parameters={},
    )
    crawl_call = PlannedToolCall(
        id="call-crawl-pdf",
        capability="web_crawler",
        query="antifraude pdf",
        rationale="extrair pdf",
        required=False,
        max_items=2,
        parameters={"depends_on": ["call-disc-pdf"]},
    )
    plan = CourseResearchPlan(
        id="plan-pdf-test",
        analysis_id="analysis-urls",
        tenant_id="ens",
        understanding_summary="antifraude",
        understanding_hash="hash-pdf",
        tool_calls=[discovery_call, crawl_call],
        budget_limit_usd=1.0,
    )

    disc_items = [
        {"url": "https://google.com", "organicResults": [{"url": pdf_url, "title": "Treinamento Antifraude 2021 PDF"}]}
    ]
    crawl_items = [
        {
            "url": pdf_url,
            "httpStatusCode": 200,
            "contentType": "application/pdf",
            "title": "Treinamento Antifraude Swiss Re 2021",
            "text": "Ementa do treinamento corporativo de detecção de fraudes em regulação de sinistros 2021...",
        }
    ]
    executor = UrlMockExecutor(payloads={"call-disc-pdf": disc_items, "call-crawl-pdf": crawl_items})

    service = CollectMarketEvidenceService(
        session=session,
        executor=executor,
        registry=registry,
    )

    outcome = await service.collect(tenant_id="ens", plan=plan)
    assert "call-crawl-pdf" in outcome.completed_call_ids

    run_row = (
        await session.execute(
            select(ToolRunModel).where(
                ToolRunModel.research_plan_id == plan.id,
                ToolRunModel.planned_call_id == "call-crawl-pdf",
            )
        )
    ).scalar_one()

    audit = run_row.parameters
    assert "url_outcomes" in audit
    assert audit["url_outcomes"][pdf_url] == "fetched"

    evidence_row = (
        await session.execute(
            select(MarketEvidenceModel).where(
                MarketEvidenceModel.tool_run_id == run_row.id,
            )
        )
    ).scalar_one()

    assert evidence_row.source_url == pdf_url
    assert "application/pdf" in str(evidence_row.raw_payload.get("contentType"))

