"""Testes de integração para amostragem estratificada, paginação e linhagem de entidades.

Valida requisitos da Tarefa 2.2 do plano de inteligência de mercado:
- Quotas e amostragem estratificada por vídeo no YouTube (evita monopolização por 1 vídeo)
- Diagnóstico explícito de truncamento de dataset quando dataset > itens lidos
- Separação estrita entre Captura (observação pontual) e Entidade (ativo de mercado canônico)
- Rastreamento de múltiplas versões/atualizações da mesma entidade sem inflar contagens de concorrentes
- Teto financeiro e falha parcial com diagnóstico
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.collect_market_evidence import CollectMarketEvidenceService
from prometeus.domain.analyses import Analysis
from prometeus.domain.configuration import AppSettings
from prometeus.domain.market_entities import (
    EntityLineageTracker,
    extract_canonical_entity_id,
)
from prometeus.domain.research import CourseResearchPlan, PlannedToolCall
from prometeus.infrastructure.apify.client import ApifyExecutionResult, ApifyRunMetadata
from prometeus.infrastructure.apify.registry import ApifyActorRegistry
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base, ToolRunModel


def test_extract_canonical_entity_id_by_capability():
    # Meta Ads
    ad_item = {"ad_archive_id": "123456789", "page_name": "Seguradora X"}
    assert extract_canonical_entity_id("meta_ads", ad_item) == "ad:123456789"

    # LinkedIn Jobs
    job_item = {"jobId": "987654321", "title": "Analista de Sinistros"}
    assert extract_canonical_entity_id("linkedin_jobs", job_item) == "job:987654321"

    # YouTube Comments
    comment_item = {"cid": "Ugx_Comment_ABC", "videoId": "vid_123", "text": "Ótimo curso"}
    assert extract_canonical_entity_id("youtube_comments", comment_item) == "comment:Ugx_Comment_ABC"

    # Web Crawler Offer
    crawler_item = {"url": "https://escola.com.br/curso-fraudes?utm_source=test", "title": "MBA"}
    assert extract_canonical_entity_id("web_crawler", crawler_item) == "offer:https://escola.com.br/curso-fraudes"


def test_entity_lineage_tracker_separates_captures_from_entities():
    tracker = EntityLineageTracker()

    # Capture 1 of Ad A
    tracker.record_capture(
        capability="meta_ads",
        item={"ad_archive_id": "AD_001", "ad_delivery_start_time": "2026-01-01", "page_name": "ENS"},
        tool_run_id="run_1",
        captured_at=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
    )
    # Capture 2 of Ad A (same entity re-observed in another run with updated status)
    tracker.record_capture(
        capability="meta_ads",
        item={"ad_archive_id": "AD_001", "ad_delivery_stop_time": "2026-02-01", "page_name": "ENS"},
        tool_run_id="run_2",
        captured_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
    )
    # Capture 1 of Ad B
    tracker.record_capture(
        capability="meta_ads",
        item={"ad_archive_id": "AD_002", "page_name": "Concorrente Y"},
        tool_run_id="run_2",
        captured_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
    )

    assert tracker.total_captures == 3
    assert tracker.unique_entities_count == 2
    assert tracker.duplicate_captures_count == 1

    entity_a = tracker.get_entity("ad:AD_001")
    assert entity_a is not None
    assert entity_a.capture_count == 2
    assert len(entity_a.versions) == 2
    assert entity_a.has_updates is True


def test_youtube_stratified_sampling_across_three_eligible_videos():
    urls = [
        "https://www.youtube.com/watch?v=VIDEO_AAA",
        "https://www.youtube.com/watch?v=VIDEO_BBB",
        "https://www.youtube.com/watch?v=VIDEO_CCC",
    ]
    call = PlannedToolCall(
        id="call-yt",
        capability="youtube_comments",
        query="fraudes em seguros",
        required=False,
        rationale="Comentários de vídeos para percepção social",
        max_items=15,
        parameters={"urls": urls},
    )

    # Scraper returned 45 items (15 from each video)
    items = []
    for vid, v_url in [("VIDEO_AAA", urls[0]), ("VIDEO_BBB", urls[1]), ("VIDEO_CCC", urls[2])]:
        for i in range(15):
            items.append({
                "cid": f"cid_{vid}_{i}",
                "videoId": vid,
                "videoUrl": v_url,
                "text": f"Comentário {i} do vídeo {vid}",
            })

    result = ApifyExecutionResult(
        run=ApifyRunMetadata(
            run_id="run-yt-1",
            dataset_id="ds-yt-1",
            status="SUCCEEDED",
            actor_id="streamers/youtube-comments-scraper",
            build_number="0.0.1",
            cost_usd=0.03,
        ),
        items=items,
        total_items=45,
    )

    retained, rejected = CollectMarketEvidenceService._normalized_items(call, result)

    assert len(retained) == 15
    # Verify each video got exactly 5 comments (stratified sampling)
    counts = {}
    for r in retained:
        counts[r["videoUrl"]] = counts.get(r["videoUrl"], 0) + 1

    assert counts[urls[0]] == 5
    assert counts[urls[1]] == 5
    assert counts[urls[2]] == 5


def test_dataset_truncation_diagnostic_is_recorded_in_audit():
    call = PlannedToolCall(
        id="call-yt-trunc",
        capability="youtube_comments",
        query="fraudes",
        required=False,
        rationale="Comentários de vídeos para teste de truncamento",
        max_items=15,
        parameters={"urls": ["https://www.youtube.com/watch?v=VIDEO_AAA"]},
    )
    items = [
        {"cid": f"cid_{i}", "videoId": "VIDEO_AAA", "text": f"Comentário {i}"}
        for i in range(15)
    ]
    # Dataset total reported by Apify header is 44, but only 15 items read
    result = ApifyExecutionResult(
        run=ApifyRunMetadata(
            run_id="run-trunc",
            dataset_id="ds-trunc",
            status="SUCCEEDED",
            actor_id="streamers/youtube-comments-scraper",
            build_number="0.0.1",
            cost_usd=0.05,
        ),
        items=items,
        total_items=44,
    )

    sampling_audit = CollectMarketEvidenceService._build_sampling_audit(
        call=call,
        result=result,
        retained_items=items,
        rejected_items=[],
    )

    assert sampling_audit["dataset_total_items"] == 44
    assert sampling_audit["items_read"] == 15
    assert sampling_audit["items_retained"] == 15
    assert sampling_audit["truncation_detected"] is True
    assert "mais itens que o limite" in sampling_audit["truncation_reason"]


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        analysis = Analysis.create(tenant_id="ens", course_name="MBA", correlation_id="test-sampling")
        analysis.id = "analysis-sampling"
        await AnalysisRepository(db).save(analysis)
        await db.commit()
        yield db
    await engine.dispose()


def make_registry():
    return ApifyActorRegistry.from_settings(
        AppSettings(
            _env_file=None,
            APIFY_ACTOR_GOOGLE_SEARCH="apify/google-search-scraper@0.0.474",
            APIFY_ACTOR_WEB_CRAWLER="apify/website-content-crawler@0.3.102",
            APIFY_ACTOR_YOUTUBE_COMMENTS="streamers/youtube-comments-scraper@0.0.257",
            APIFY_ACTOR_INSTAGRAM="apify/instagram-scraper@0.0.831",
        )
    )


@dataclass
class MockExecutor:
    payloads: dict[str, list[dict]]
    total_items_map: dict[str, int] = field(default_factory=dict)
    statuses: dict[str, str] = field(default_factory=dict)
    calls: list[PlannedToolCall] = field(default_factory=list)

    async def execute(self, planned: PlannedToolCall, *, max_total_charge_usd: float) -> ApifyExecutionResult:
        self.calls.append(planned)
        registry = make_registry()
        spec = registry.require(planned.capability)
        items = self.payloads.get(planned.id, [])
        status = self.statuses.get(planned.id, "SUCCEEDED")
        total_items = self.total_items_map.get(planned.id, len(items))
        return ApifyExecutionResult(
            run=ApifyRunMetadata(
                run_id=f"run-{planned.id}",
                dataset_id=f"ds-{planned.id}",
                status=status,
                actor_id=spec.actor_id,
                build_number=spec.build,
                cost_usd=0.02,
                incomplete_reason="partial error" if status == "PARTIAL" else None,
            ),
            items=items,
            total_items=total_items,
        )




@pytest.mark.asyncio
async def test_collect_service_persists_sampling_and_entities_audit(session):
    registry = make_registry()
    urls = [
        "https://www.youtube.com/watch?v=VID_1",
        "https://www.youtube.com/watch?v=VID_2",
        "https://www.youtube.com/watch?v=VID_3",
    ]
    # Discovery call that finds the 3 URLs, then YouTube comments call
    discovery_call = PlannedToolCall(
        id="call-disc",
        capability="google_search",
        query="site:youtube.com fraudes",
        rationale="descobrir videos",
        required=False,
        max_items=5,
        parameters={},
    )
    yt_call = PlannedToolCall(
        id="call-yt",
        capability="youtube_comments",
        query="comentarios",
        rationale="coletar comentarios",
        required=False,
        max_items=9,
        parameters={"depends_on": ["call-disc"]},
    )
    plan = CourseResearchPlan(
        id="plan-sampling-1",
        analysis_id="analysis-sampling",
        tenant_id="ens",
        understanding_summary="fraudes",
        understanding_hash="hash-123",
        tool_calls=[discovery_call, yt_call],
        budget_limit_usd=1.0,
    )

    disc_items = [
        {"url": "https://www.google.com/search?q=test", "organicResults": [{"url": u, "title": f"Video {u}"} for u in urls]}
    ]
    yt_items = [
        {"cid": f"cid_{v}_{i}", "videoId": v.replace("https://www.youtube.com/watch?v=", ""), "videoUrl": v, "text": f"Comentário {i} em {v}"}
        for v in urls
        for i in range(5)
    ]
    executor = MockExecutor(
        payloads={"call-disc": disc_items, "call-yt": yt_items},
        total_items_map={"call-yt": 45},
    )

    service = CollectMarketEvidenceService(
        session=session,
        executor=executor,
        registry=registry,
    )

    outcome = await service.collect(tenant_id="ens", plan=plan)
    assert "call-yt" in outcome.completed_call_ids

    run_row = (
        await session.execute(
            select(ToolRunModel).where(
                ToolRunModel.research_plan_id == plan.id,
                ToolRunModel.planned_call_id == "call-yt",
            )
        )
    ).scalar_one()

    audit = run_row.parameters
    assert "sampling" in audit
    assert "entities" in audit

    sampling = audit["sampling"]
    assert sampling["limit_unit"] == "per_video"
    assert sampling["dataset_total_items"] == 45
    assert sampling["sampling_strategy"] == "stratified_per_video"
    assert sampling["truncation_detected"] is True

    entities = audit["entities"]
    assert entities["unique_entities_count"] > 0
    assert "comment" in entities["entity_types"]


@pytest.mark.asyncio
async def test_entity_lineage_tracker_distinguishes_multiple_captures_without_multiplying_competitors():
    tracker = EntityLineageTracker()

    # Call 1 captures Job 101
    tracker.record_capture(
        capability="linkedin_jobs",
        item={"jobId": "JOB_101", "title": "Perito de Fraudes", "companyName": "Seguradora Alpha"},
        tool_run_id="run_101",
    )
    # Call 2 captures same Job 101 (same canonical entity)
    tracker.record_capture(
        capability="linkedin_jobs",
        item={"jobId": "JOB_101", "title": "Perito de Fraudes Sênior", "companyName": "Seguradora Alpha"},
        tool_run_id="run_102",
    )
    # Call 3 captures different Job 202
    tracker.record_capture(
        capability="linkedin_jobs",
        item={"jobId": "JOB_202", "title": "Analista de Sinistro", "companyName": "Seguradora Beta"},
        tool_run_id="run_103",
    )

    assert tracker.total_captures == 3
    assert tracker.unique_entities_count == 2
    assert tracker.duplicate_captures_count == 1
    assert tracker.distinct_entities_by_type["job"] == 2


@pytest.mark.asyncio
async def test_financial_budget_enforcement_aborts_excessive_run(session):
    registry = make_registry()
    call_1 = PlannedToolCall(
        id="call-exp-1",
        capability="google_search",
        query="curso seguros 1",
        rationale="teste orcamento 1",
        required=False,
        max_items=5,
        parameters={},
    )
    call_2 = PlannedToolCall(
        id="call-exp-2",
        capability="google_search",
        query="curso seguros 2",
        rationale="teste orcamento 2",
        required=False,
        max_items=5,
        parameters={},
    )
    # Plan with very tight budget of $0.03
    plan = CourseResearchPlan(
        id="plan-budget-test",
        analysis_id="analysis-sampling",
        tenant_id="ens",
        understanding_summary="fraudes",
        understanding_hash="hash-budget",
        tool_calls=[call_1, call_2],
        budget_limit_usd=0.03,
    )

    executor = MockExecutor(
        payloads={"call-exp-1": [{"url": "https://google.com"}], "call-exp-2": [{"url": "https://google.com"}]},
    )

    service = CollectMarketEvidenceService(
        session=session,
        executor=executor,
        registry=registry,
    )

    outcome = await service.collect(tenant_id="ens", plan=plan)
    # First call costs $0.02, second call exceeds remaining budget ($0.02 > $0.01)
    assert "call-exp-1" in outcome.completed_call_ids
    assert "call-exp-2" in outcome.optional_failures

    run_row = (
        await session.execute(
            select(ToolRunModel).where(
                ToolRunModel.research_plan_id == plan.id,
                ToolRunModel.planned_call_id == "call-exp-2",
            )
        )
    ).scalar_one()
    assert run_row.status == "FAILED"
    assert run_row.error_code == "budget_exceeded"


@pytest.mark.asyncio
async def test_partial_failure_in_multi_video_call(session):
    registry = make_registry()
    discovery_call = PlannedToolCall(
        id="call-disc-part",
        capability="google_search",
        query="site:youtube.com fraudes",
        rationale="descobrir videos",
        required=False,
        max_items=5,
        parameters={},
    )
    yt_call = PlannedToolCall(
        id="call-yt-part",
        capability="youtube_comments",
        query="comentarios",
        rationale="coletar comentarios com falha parcial",
        required=False,
        max_items=9,
        parameters={"depends_on": ["call-disc-part"]},
    )
    plan = CourseResearchPlan(
        id="plan-partial-test",
        analysis_id="analysis-sampling",
        tenant_id="ens",
        understanding_summary="fraudes",
        understanding_hash="hash-part",
        tool_calls=[discovery_call, yt_call],
        budget_limit_usd=1.0,
    )

    urls = ["https://www.youtube.com/watch?v=VID_OK", "https://www.youtube.com/watch?v=VID_ERR"]
    disc_items = [
        {"url": "https://www.google.com/search?q=test", "organicResults": [{"url": u, "title": f"Video {u}"} for u in urls]}
    ]
    yt_items = [
        {"cid": f"cid_ok_{i}", "videoId": "VID_OK", "videoUrl": urls[0], "text": f"Comentário {i}"}
        for i in range(5)
    ]
    executor = MockExecutor(
        payloads={"call-disc-part": disc_items, "call-yt-part": yt_items},
        statuses={"call-yt-part": "PARTIAL"},
    )

    service = CollectMarketEvidenceService(
        session=session,
        executor=executor,
        registry=registry,
    )

    outcome = await service.collect(tenant_id="ens", plan=plan)
    assert "call-yt-part" in outcome.optional_failures

    run_row = (
        await session.execute(
            select(ToolRunModel).where(
                ToolRunModel.research_plan_id == plan.id,
                ToolRunModel.planned_call_id == "call-yt-part",
            )
        )
    ).scalar_one()

    assert run_row.status == "PARTIAL"
    assert run_row.error_code == "timeout"
    assert "partial error" in (run_row.error_message or "")


