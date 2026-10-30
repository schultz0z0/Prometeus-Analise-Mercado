from dataclasses import dataclass, field

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.collect_market_evidence import CollectMarketEvidenceService
from prometeus.domain.analyses import Analysis
from prometeus.domain.configuration import AppSettings
from prometeus.domain.research import CourseResearchPlan, PlannedToolCall
from prometeus.infrastructure.apify.registry import ActorConfigurationError, ApifyActorRegistry
from prometeus.infrastructure.apify.schemas import ApifyExecutionResult, ApifyRunMetadata
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base, MarketEvidenceModel, ToolRunModel


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        analysis = Analysis.create(tenant_id="ens", course_name="MBA", correlation_id="test")
        analysis.id = "integrity"
        await AnalysisRepository(db).save(analysis)
        await db.commit()
        yield db
    await engine.dispose()


def registry():
    return ApifyActorRegistry.from_settings(
        AppSettings(
            _env_file=None,
            APIFY_ACTOR_GOOGLE_SEARCH="apify/google-search-scraper@0.0.474",
            APIFY_ACTOR_WEB_CRAWLER="apify/website-content-crawler@0.3.102",
            APIFY_ACTOR_YOUTUBE_COMMENTS="streamers/youtube-comments-scraper@0.0.257",
            APIFY_ACTOR_INSTAGRAM="apify/instagram-scraper@0.0.831",
        )
    )


def call(cid, capability="google_search", **parameters):
    return PlannedToolCall(
        id=cid,
        capability=capability,
        query="curso seguros",
        rationale="test",
        required=False,
        max_items=5,
        parameters=parameters,
    )


@dataclass
class Executor:
    payloads: dict
    calls: list = field(default_factory=list)

    async def execute(self, planned, *, max_total_charge_usd):
        self.calls.append(planned)
        spec = registry().require(planned.capability)
        items = self.payloads.get(planned.id, [])
        return ApifyExecutionResult(
            run=ApifyRunMetadata(
                run_id=planned.id,
                dataset_id=planned.id,
                status="SUCCEEDED",
                actor_id=spec.actor_id,
                build_number=spec.build,
                cost_usd=0.01,
            ),
            items=items,
            total_items=0,
        )


def plan(calls):
    return CourseResearchPlan(
        id="integrity-plan",
        analysis_id="integrity",
        understanding_hash="a" * 64,
        tool_calls=calls,
        budget_limit_usd=1,
    )


async def test_partial_result_keeps_evidence_cost_and_failure_on_resume(session):
    class PartialExecutor(Executor):
        async def execute(self, planned, *, max_total_charge_usd):
            result = await super().execute(planned, max_total_charge_usd=max_total_charge_usd)
            return result.model_copy(
                update={
                    "run": result.run.model_copy(
                        update={
                            "status": "ABORTED",
                            "incomplete_reason": "Timeout; cancelamento confirmado.",
                        }
                    )
                }
            )

    executor = PartialExecutor(
        {"partial": [{"url": "https://example.edu/curso", "title": "Curso de seguros"}]}
    )
    service = CollectMarketEvidenceService(session, executor, registry())
    research = plan([call("partial")])
    first = await service.collect(tenant_id="ens", plan=research)
    resumed = await service.collect(tenant_id="ens", plan=research)
    run = (await session.execute(select(ToolRunModel))).scalar_one()
    assert run.status == "PARTIAL"
    assert run.error_code == "timeout"
    assert run.dataset_id == "partial"
    assert len(first.evidence_ids) == 1
    assert resumed.evidence_ids == first.evidence_ids
    assert first.optional_failures == resumed.optional_failures == ["partial"]
    assert first.spent_usd == resumed.spent_usd == 0.01
    assert len(executor.calls) == 1


async def test_instagram_no_items_remains_a_diagnostic_without_market_evidence(session):
    executor = Executor(
        {
            "insta": [
                {
                    "error": "no_items",
                    "errorDescription": "Empty or private data for provided input",
                }
            ]
        }
    )
    outcome = await CollectMarketEvidenceService(session, executor, registry()).collect(
        tenant_id="ens", plan=plan([call("insta", "instagram")])
    )
    run = (await session.execute(select(ToolRunModel))).scalar_one()
    assert run.status == "EMPTY"
    assert run.parameters["observation_status"] == "rejected_items"
    assert run.provider_run_id == "insta"
    assert "no_items" in run.parameters["rejected_items"][0]["raw_json"]
    assert not outcome.evidence_ids


async def test_timeout_without_usable_items_keeps_observed_cost_once(session):
    from prometeus.infrastructure.apify.client import ApifyTimeoutError

    class TimeoutExecutor:
        async def execute(self, planned, *, max_total_charge_usd):
            raise ApifyTimeoutError(
                "Timeout",
                run_id="slow",
                run_data={
                    "status": "ABORTED",
                    "defaultDatasetId": "empty-dataset",
                    "usageTotalUsd": 0.13,
                },
            )

    service = CollectMarketEvidenceService(session, TimeoutExecutor(), registry())
    research = plan([call("slow")])
    first = await service.collect(tenant_id="ens", plan=research)
    resumed = await service.collect(tenant_id="ens", plan=research)
    run = (await session.execute(select(ToolRunModel))).scalar_one()
    assert first.spent_usd == resumed.spent_usd == 0.13
    assert run.cost_usd == 0.13
    assert run.dataset_id == "empty-dataset"
    assert run.status == "FAILED"


async def test_partial_crawl_does_not_recrawl_emitted_urls_but_keeps_unvisited_seeds(session):
    class PartialExecutor(Executor):
        async def execute(self, planned, *, max_total_charge_usd):
            result = await super().execute(planned, max_total_charge_usd=max_total_charge_usd)
            if planned.id == "crawl-first":
                return result.model_copy(
                    update={
                        "run": result.run.model_copy(
                            update={"status": "ABORTED", "incomplete_reason": "Timeout"}
                        )
                    }
                )
            return result

    executor = PartialExecutor(
        {
            "search": [
                {"url": "https://example.edu/a", "title": "A"},
                {"url": "https://example.edu/b", "title": "B"},
            ],
            "crawl-first": [
                {"url": "https://example.edu/b", "text": "B, página seguida antes do timeout"}
            ],
            "crawl-again": [{"url": "https://example.edu/a", "text": "A, seed ainda não visitada"}],
        }
    )
    service = CollectMarketEvidenceService(session, executor, registry())
    await service.collect(
        tenant_id="ens",
        plan=plan(
            [
                call("search"),
                call("crawl-first", "web_crawler", depends_on=["search"]),
                call("crawl-again", "web_crawler", depends_on=["search"]),
            ]
        ),
    )
    assert executor.calls[-1].parameters["urls"] == ["https://example.edu/a"]


async def test_schema_drift_keeps_known_run_provenance_and_cost(session):
    from prometeus.infrastructure.apify.client import ApifySchemaDriftError

    class DriftExecutor:
        async def execute(self, planned, *, max_total_charge_usd):
            raise ApifySchemaDriftError(
                "Build divergente",
                run_data={
                    "id": "drift-run",
                    "status": "ABORTED",
                    "defaultDatasetId": "drift-dataset",
                    "usageTotalUsd": 0.13,
                },
            )

    service = CollectMarketEvidenceService(session, DriftExecutor(), registry())
    outcome = await service.collect(tenant_id="ens", plan=plan([call("drift")]))
    run = (await session.execute(select(ToolRunModel))).scalar_one()
    assert outcome.spent_usd == run.cost_usd == 0.13
    assert run.provider_run_id == "drift-run"
    assert run.dataset_id == "drift-dataset"
    assert run.status == "FAILED"
    assert run.error_code == "schema_drift"
    assert not outcome.evidence_ids


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/channel/abc",
        "https://youtube.com/@ens",
        "https://youtube.com/watch",
        "https://youtu.be/",
        "https://youtube.com/watch?v=",
        "https://youtube.com/watch?v=video&url=http://localhost/",
    ],
)
def test_youtube_discovery_requires_video_identifier(url):
    # Extra query parameters are permitted; the last example is a real video URL.
    if "v=video" in url:
        assert CollectMarketEvidenceService._is_usable_discovered_url("youtube_comments", url)
    else:
        assert not CollectMarketEvidenceService._is_usable_discovered_url("youtube_comments", url)


async def test_dependencies_use_exact_origin_and_do_not_recrawl_visited_urls(session):
    calls = [
        call("crawl-b", "web_crawler", depends_on=["search-b"]),
        call("search-a"),
        call("search-b"),
        call("crawl-a", "web_crawler", depends_on=["search-a"]),
        call("crawl-again", "web_crawler", depends_on=["search-a"]),
    ]
    executor = Executor(
        {
            "search-a": [{"url": "https://example.edu/a?utm_source=google", "title": "A"}],
            "search-b": [{"url": "https://example.edu/b", "title": "B"}],
            "crawl-a": [{"url": "https://example.edu/a", "text": "Curso A"}],
            "crawl-b": [{"url": "https://example.edu/b", "text": "Curso B"}],
        }
    )
    service = CollectMarketEvidenceService(session, executor, registry())
    await service.collect(tenant_id="ens", plan=plan(calls))
    seen = {c.id: c for c in executor.calls}
    assert seen["crawl-b"].parameters["urls"] == ["https://example.edu/b"]
    assert seen["crawl-a"].parameters["urls"] == ["https://example.edu/a?utm_source=google"]
    assert "crawl-again" not in seen


async def test_serp_results_are_individual_evidences_with_discovery_provenance(session):
    executor = Executor(
        {
            "search": [
                {
                    "url": "https://google.com/search?q=curso",
                    "organicResults": [
                        {"url": "https://example.edu/a", "title": "A", "position": 1},
                        {"url": "https://example.edu/b", "title": "B", "position": 2},
                    ],
                }
            ]
        }
    )
    await CollectMarketEvidenceService(session, executor, registry()).collect(
        tenant_id="ens", plan=plan([call("search")])
    )
    rows = list((await session.execute(select(MarketEvidenceModel))).scalars())
    assert {r.source_url for r in rows} == {"https://example.edu/a", "https://example.edu/b"}
    assert {r.raw_payload["_discovery"]["query"] for r in rows} == {"curso seguros"}
    assert {r.raw_payload["_discovery"]["rank"] for r in rows} == {1, 2}
    run = (await session.execute(select(ToolRunModel))).scalar_one()
    assert run.raw_items_count == 1
    assert run.valid_items_count == 2
    assert run.parameters["dataset_total_items"] == 0


async def test_supplied_urls_must_be_discovered_and_invalid_values_are_filtered(session):
    executor = Executor(
        {
            "search": [{"url": "https://example.edu/a", "title": "A"}],
            "crawl": [{"url": "https://example.edu/a", "text": "A"}],
        }
    )
    await CollectMarketEvidenceService(session, executor, registry()).collect(
        tenant_id="ens",
        plan=plan(
            [
                call("search"),
                call(
                    "crawl",
                    "web_crawler",
                    depends_on=["search"],
                    urls=["file:///etc/passwd", "https://invented.edu/", "https://example.edu/a"],
                ),
            ]
        ),
    )
    assert executor.calls[-1].parameters["urls"] == ["https://example.edu/a"]


async def test_unknown_dependency_is_rejected_before_any_provider_call(session):
    executor = Executor({})
    with pytest.raises((ActorConfigurationError, ValueError), match="depend"):
        await CollectMarketEvidenceService(session, executor, registry()).collect(
            tenant_id="ens", plan=plan([call("crawl", "web_crawler", depends_on=["missing"])])
        )
    assert executor.calls == []


async def test_channel_and_hashtag_metadata_are_audited_but_not_counted(session):
    executor = Executor(
        {
            "instagram": [
                {
                    "url": "https://instagram.com/explore/tags/seguros/",
                    "name": "seguros",
                    "postsCount": 1000,
                }
            ]
        }
    )
    service = CollectMarketEvidenceService(session, executor, registry())
    research_plan = plan([call("instagram", "instagram")])
    await service.collect(tenant_id="ens", plan=research_plan)
    await service.collect(tenant_id="ens", plan=research_plan)
    assert len(executor.calls) == 1
    assert list((await session.execute(select(MarketEvidenceModel))).scalars()) == []
    run = (await session.execute(select(ToolRunModel))).scalar_one()
    assert run.status == "EMPTY"
    assert run.parameters["observation_status"] == "rejected_items"
    assert run.parameters["rejected_items"][0]["reason"]
    assert run.cost_usd == 0.01


async def test_observed_empty_is_distinct_from_rejected_items(session):
    executor = Executor({})
    await CollectMarketEvidenceService(session, executor, registry()).collect(
        tenant_id="ens", plan=plan([call("search")])
    )
    run = (await session.execute(select(ToolRunModel))).scalar_one()
    assert run.parameters["observation_status"] == "observed_empty"


async def test_crawler_does_not_charge_again_for_pages_followed_from_a_previous_seed(session):
    executor = Executor(
        {
            "search-a": [{"url": "https://example.edu/a", "title": "A"}],
            "search-b": [{"url": "https://example.edu/b", "title": "B"}],
            "crawl-a": [
                {"url": "https://example.edu/a", "text": "Curso A"},
                {"url": "https://example.edu/b", "text": "Curso B encontrado seguindo A"},
            ],
            "crawl-b": [{"url": "https://example.edu/b", "text": "Curso B repetido"}],
        }
    )
    service = CollectMarketEvidenceService(session, executor, registry())
    outcome = await service.collect(
        tenant_id="ens",
        plan=plan(
            [
                call("search-a"),
                call("search-b"),
                call("crawl-a", "web_crawler", depends_on=["search-a"]),
                call("crawl-b", "web_crawler", depends_on=["search-b"]),
            ]
        ),
    )
    assert "crawl-b" not in [planned.id for planned in executor.calls]
    assert outcome.spent_usd == 0.03


async def test_youtube_channel_metadata_with_text_is_not_a_comment_even_with_video_origin(session):
    executor = Executor(
        {
            "search": [{"url": "https://youtube.com/watch?v=video", "title": "Aula"}],
            "youtube": [
                {
                    "channelUrl": "https://youtube.com/channel/UCschool",
                    "channelName": "Escola",
                    "text": "Canal da Escola",
                }
            ],
        }
    )
    service = CollectMarketEvidenceService(session, executor, registry())
    await service.collect(
        tenant_id="ens",
        plan=plan(
            [
                call("search"),
                call("youtube", "youtube_comments", depends_on=["search"]),
            ]
        ),
    )
    rows = list((await session.execute(select(MarketEvidenceModel))).scalars())
    assert all(row.source_name != "apify_youtube_comments" for row in rows)
    run = (
        await session.execute(
            select(ToolRunModel).where(ToolRunModel.capability == "youtube_comments")
        )
    ).scalar_one()
    assert run.parameters["observation_status"] == "rejected_items"


async def test_distinct_comments_from_same_video_keep_their_identity_and_provenance(session):
    executor = Executor(
        {
            "search": [{"url": "https://youtube.com/watch?v=video", "title": "Aula"}],
            "youtube": [
                {"cid": "comment-a", "text": "Quero uma aula prática.", "channelName": "Escola"},
                {"cid": "comment-b", "text": "Quero mais exercícios.", "channelName": "Escola"},
            ],
        }
    )
    service = CollectMarketEvidenceService(session, executor, registry())
    await service.collect(
        tenant_id="ens",
        plan=plan(
            [
                call("search"),
                call("youtube", "youtube_comments", depends_on=["search"]),
            ]
        ),
    )
    rows = list(
        (
            await session.execute(
                select(MarketEvidenceModel).where(
                    MarketEvidenceModel.source_name == "apify_youtube_comments"
                )
            )
        ).scalars()
    )
    assert len(rows) == 2
    assert {row.source_url for row in rows} == {"https://youtube.com/watch?v=video"}


async def test_multi_video_comment_without_link_is_quarantined_instead_of_assigned_first_video(
    session,
):
    executor = Executor(
        {
            "search": [
                {"url": "https://youtube.com/watch?v=first", "title": "Aula A"},
                {"url": "https://youtube.com/watch?v=second", "title": "Aula B"},
            ],
            "youtube": [{"cid": "comment-a", "text": "Quero aprender mais."}],
        }
    )
    await CollectMarketEvidenceService(session, executor, registry()).collect(
        tenant_id="ens",
        plan=plan(
            [
                call("search"),
                call("youtube", "youtube_comments", depends_on=["search"]),
            ]
        ),
    )
    rows = list(
        (
            await session.execute(
                select(MarketEvidenceModel).where(
                    MarketEvidenceModel.source_name == "apify_youtube_comments"
                )
            )
        ).scalars()
    )
    assert rows == []


async def test_multi_video_comment_uses_matching_video_id_and_not_channel_url(session):
    executor = Executor(
        {
            "search": [
                {"url": "https://youtube.com/watch?v=first", "title": "Aula A"},
                {"url": "https://youtube.com/watch?v=second", "title": "Aula B"},
            ],
            "youtube": [
                {
                    "cid": "comment-a",
                    "text": "Quero aprender mais.",
                    "videoId": "second",
                    "url": "https://youtube.com/channel/UCschool",
                    "channelUrl": "https://youtube.com/channel/UCschool",
                }
            ],
        }
    )
    await CollectMarketEvidenceService(session, executor, registry()).collect(
        tenant_id="ens",
        plan=plan(
            [
                call("search"),
                call("youtube", "youtube_comments", depends_on=["search"]),
            ]
        ),
    )
    row = (
        await session.execute(
            select(MarketEvidenceModel).where(
                MarketEvidenceModel.source_name == "apify_youtube_comments"
            )
        )
    ).scalar_one()
    assert row.source_url == "https://youtube.com/watch?v=second"
