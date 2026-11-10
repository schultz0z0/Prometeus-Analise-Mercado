import hashlib
import json

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.collect_market_evidence import CollectMarketEvidenceService
from prometeus.domain.analyses import Analysis
from prometeus.domain.configuration import AppSettings
from prometeus.domain.research import CourseResearchPlan, PlannedToolCall
from prometeus.infrastructure.apify.client import ApifyActorFailedError, ApifySchemaDriftError
from prometeus.infrastructure.apify.registry import ApifyActorRegistry
from prometeus.infrastructure.apify.schemas import ApifyExecutionResult, ApifyRunMetadata
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base


def registry():
    return ApifyActorRegistry.from_settings(
        AppSettings(
            _env_file=None,
            APIFY_ACTOR_GOOGLE_SEARCH="apify/google-search-scraper@0.0.473",
            APIFY_ACTOR_YOUTUBE_COMMENTS="streamers/youtube-comments-scraper@0.0.257",
            APIFY_ACTOR_INSTAGRAM="apify/instagram-scraper@0.0.831",
        )
    )


def result(capability, items, total=None):
    actor = registry().require(capability)
    return ApifyExecutionResult(
        run=ApifyRunMetadata(
            run_id="provider-run",
            dataset_id="provider-dataset",
            status="SUCCEEDED",
            actor_id=actor.actor_id,
            build_number=actor.build,
        ),
        items=items,
        total_items=len(items) if total is None else total,
        total_items_source="provider_pagination",
    )


def test_normalization_keeps_every_serp_child_and_its_source_pointer():
    call = PlannedToolCall(capability="google_search", query="curso", rationale="test", max_items=1)
    children = [
        {"title": str(i), "url": f"https://school.test/{i}", "custom": {"tail": i}}
        for i in range(8)
    ]
    source = {
        "organicResults": children,
        "paidResults": [{"title": "Paid context"}],
        "customParent": "Retain this too",
    }
    retained, rejected = CollectMarketEvidenceService._normalized_items(
        call, result("google_search", [source])
    )
    assert len(retained) == 8
    assert not rejected
    assert retained[-1]["custom"] == {"tail": 7}
    assert retained[-1]["_source_record"] == {"index": 0, "pointer": "/organicResults/7"}


def test_normalization_keeps_every_returned_comment_from_each_video():
    urls = [
        "https://www.youtube.com/watch?v=VIDEO_AAA",
        "https://www.youtube.com/watch?v=VIDEO_BBB",
    ]
    call = PlannedToolCall(
        capability="youtube_comments",
        query="curso",
        rationale="test",
        max_items=1,
        parameters={"urls": urls},
    )
    items = [
        {"cid": f"{video}-{i}", "videoUrl": video, "text": f"Comment {i}"}
        for video in urls
        for i in range(4)
    ]
    retained, rejected = CollectMarketEvidenceService._normalized_items(
        call, result("youtube_comments", items)
    )
    assert len(retained) == 8
    assert not rejected


@pytest.mark.asyncio
async def test_archive_preserves_all_original_rows_duplicates_and_full_diagnostics():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        analysis = Analysis.create(tenant_id="ens", course_name="Curso", correlation_id="archive")
        await AnalysisRepository(session).save(analysis)
        await session.commit()
        call = PlannedToolCall(capability="instagram", query="curso", rationale="test", max_items=1)
        plan = CourseResearchPlan(
            analysis_id=analysis.id, understanding_hash="hash", tool_calls=[call]
        )
        service = CollectMarketEvidenceService(session, None, registry())
        await service._ensure_plan(tenant_id="ens", plan=plan, understanding_snapshot={})
        run = await service._checkpoint_running(plan=plan, call=call)
        duplicate = {
            "caption": "Educational content",
            "shortCode": "post-a",
            "url": "https://www.instagram.com/p/post-a",
        }
        rows = [duplicate, duplicate] + [
            {"error": "no_items", "diagnostic": "x" * 6000, "email": "private@example.test"}
            for _ in range(12)
        ]
        await service._persist_result(call=call, run=run, result=result("instagram", rows))
        archive = run.parameters["dataset_archive"]
        assert archive["schema_version"] == 1
        assert archive["provider_run_id"] == "provider-run"
        assert archive["dataset_id"] == "provider-dataset"
        assert archive["retrieval_complete"] is True
        assert archive["items_read"] == archive["dataset_total_items"] == 14
        assert len(archive["items"]) == 14
        last = archive["items"][-1]
        assert last["index"] == 13
        assert last["raw_payload"] == rows[-1]
        assert last["sanitized_data"]["diagnostic"] == "x" * 6000
        assert last["sanitized_data"]["email"] == "[EMAIL_REDACTED]"
        assert last["sanitization_changed"] is True
        assert (
            last["source_sha256"]
            == hashlib.sha256(
                json.dumps(rows[-1], ensure_ascii=False, sort_keys=True).encode()
            ).hexdigest()
        )
        assert len(run.parameters["rejected_items"]) == 12
        assert len(run.parameters["rejected_items"][-1]["raw_json"]) > 6000
        assert "private@example.test" not in run.parameters["rejected_items"][-1]["raw_json"]
    await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["schema", "failed", "failed_pending", "timeout", "timeout_pending"])
async def test_failure_checkpoint_preserves_originals_without_admitting_evidence(failure):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        analysis = Analysis.create(
            tenant_id="ens", course_name="Curso", correlation_id="schema-archive"
        )
        await AnalysisRepository(session).save(analysis)
        await session.commit()
        call = PlannedToolCall(
            capability="google_search", query="curso", rationale="test", max_items=1
        )
        plan = CourseResearchPlan(
            analysis_id=analysis.id, understanding_hash="hash", tool_calls=[call]
        )
        service = CollectMarketEvidenceService(session, None, registry())
        await service._ensure_plan(tenant_id="ens", plan=plan, understanding_snapshot={})
        run = await service._checkpoint_running(plan=plan, call=call)
        original = {"unrecognized": "x" * 6000, "email": "private@example.test"}
        dataset_result = result("google_search", [original])
        if failure == "schema":
            error = ApifySchemaDriftError("schema changed", dataset_result=dataset_result)
        elif failure.startswith("timeout"):
            from prometeus.infrastructure.apify.client import ApifyTimeoutError
            error = ApifyTimeoutError("timeout", run_id="provider-run")
            error.dataset_result = dataset_result
            error.dataset_read_pending = failure == "timeout_pending"
        else:
            error = ApifyActorFailedError(run_id="provider-run", status="FAILED")
            error.dataset_result = dataset_result
            error.dataset_read_pending = failure == "failed_pending"
        await service._checkpoint_failure(run, error)
        assert run.status == "FAILED"
        assert run.error_code == ("schema_drift" if failure == "schema" else "timeout" if failure.startswith("timeout") else "provider_error")
        assert run.valid_items_count == 0
        archive = run.parameters["dataset_archive"]
        assert archive["retrieval_complete"] is True
        assert archive["items"][0]["raw_payload"] == original
        assert archive["items"][0]["sanitized_data"]["email"] == "[EMAIL_REDACTED]"
        assert (
            run.parameters["observation_status"]
            == {
                "schema": "schema_drift_requires_review",
                "failed": "failed_actor_dataset_retained",
                "failed_pending": "failed_actor_dataset_pending",
                "timeout": "failed_actor_dataset_retained",
                "timeout_pending": "failed_actor_dataset_pending",
            }[failure]
        )
        if failure in {"failed_pending", "timeout_pending"}:
            assert run.parameters["dataset_read_pending"] is True
            assert run.parameters["dataset_read_recovery"] == "resume_existing_provider_run"
    await engine.dispose()


@pytest.mark.asyncio
async def test_archive_does_not_claim_completeness_for_truncated_executor_output():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        analysis = Analysis.create(tenant_id="ens", course_name="Curso", correlation_id="partial")
        await AnalysisRepository(session).save(analysis)
        await session.commit()
        call = PlannedToolCall(
            capability="google_search", query="curso", rationale="test", max_items=1
        )
        plan = CourseResearchPlan(
            analysis_id=analysis.id, understanding_hash="hash", tool_calls=[call]
        )
        service = CollectMarketEvidenceService(session, None, registry())
        await service._ensure_plan(tenant_id="ens", plan=plan, understanding_snapshot={})
        run = await service._checkpoint_running(plan=plan, call=call)
        await service._persist_result(
            call=call,
            run=run,
            result=result(
                "google_search", [{"title": "One", "url": "https://school.test/1"}], total=3
            ),
        )
        assert run.status == "PARTIAL"
        assert run.parameters["dataset_archive"]["retrieval_complete"] is False
        assert run.parameters["dataset_archive"]["items_read"] == 1
    await engine.dispose()
