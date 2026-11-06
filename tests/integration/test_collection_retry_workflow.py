from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.analysis_jobs import claim_analysis_job
from prometeus.application.create_analysis import CreateAnalysisCommand, CreateAnalysisUseCase
from prometeus.application.recover_market_collection import CollectionRetryScheduled
from prometeus.application.run_course_analysis import RunCourseAnalysis
from prometeus.domain.analyses import Analysis
from prometeus.domain.configuration import AppSettings
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import AnalysisJobModel, AnalysisModel, Base


@pytest.fixture
async def database(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'collection_retry.sqlite3'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def test_retry_checkpoint_is_pending_and_preserves_running_analysis(database):
    async with database() as session:
        analysis = Analysis.create(tenant_id="ens", course_name="Coleta", correlation_id="test")
        analysis.start("test")
        await AnalysisRepository(session).save(analysis)
        await session.commit()
        workflow = object.__new__(RunCourseAnalysis)
        workflow.session = session
        workflow.repository = AnalysisRepository(session)
        due = datetime.now(UTC) + timedelta(seconds=30)

        async def collecting():
            raise CollectionRetryScheduled(due)

        with pytest.raises(CollectionRetryScheduled):
            await workflow._checkpoint(analysis, 8, collecting)
        stored = await AnalysisRepository(session).get_by_id(analysis.id)
        assert stored.status.value == "RUNNING"
        assert stored.steps[0].status == "PENDING"
        assert stored.steps[0].error_message is None
        assert stored.steps[0].output_summary["retry"]["next_attempt_at"] == due.isoformat()


async def test_future_retry_cannot_be_claimed_by_an_early_redelivery(database):
    async with database() as session:
        result = await CreateAnalysisUseCase(session, AppSettings(_env_file=None, APP_ENV="test")).execute(
            CreateAnalysisCommand("ens", "Coleta", {}, "future", "test")
        )
        job = await session.get(AnalysisJobModel, result.analysis_id)
        job.next_attempt_at = datetime.now(UTC) + timedelta(hours=1)
        await session.commit()
        assert await claim_analysis_job(session, result.analysis_id, "too-early") is False


async def test_execute_propagates_retry_without_failing_analysis(database, monkeypatch):
    async with database() as session:
        analysis = Analysis.create(tenant_id="ens", course_name="Coleta", correlation_id="test")
        await AnalysisRepository(session).save(analysis)
        await session.commit()
        workflow = object.__new__(RunCourseAnalysis)
        workflow.session = session
        workflow.repository = AnalysisRepository(session)
        workflow.settings = AppSettings(_env_file=None, APP_ENV="test")
        workflow.decisions = SimpleNamespace()

        async def pending(*args):
            raise CollectionRetryScheduled(datetime.now(UTC) + timedelta(minutes=1))

        monkeypatch.setattr(workflow, "_checkpoint", pending)
        with pytest.raises(CollectionRetryScheduled):
            await workflow.execute(analysis.id, "test")
        assert (await AnalysisRepository(session).get_by_id(analysis.id)).status.value == "RUNNING"


async def test_retry_cannot_release_another_workers_lease_or_cancelled_analysis(database):
    from prometeus.application import analysis_jobs

    async with database() as session:
        result = await CreateAnalysisUseCase(session, AppSettings(_env_file=None, APP_ENV="test")).execute(
            CreateAnalysisCommand("ens", "Coleta", {}, "retry-scope", "test")
        )
        await session.commit()
        assert await claim_analysis_job(session, result.analysis_id, "owner") is True
        helper = getattr(analysis_jobs, "schedule_analysis_job_retry", None)
        assert helper is not None
        assert await helper(session, result.analysis_id, "stale-owner", datetime.now(UTC)) is False
        analysis = await AnalysisRepository(session).get_by_id(result.analysis_id)
        analysis.cancel("test")
        await AnalysisRepository(session).save(analysis)
        await session.commit()
        assert await helper(session, result.analysis_id, "owner", datetime.now(UTC)) is False


@pytest.mark.parametrize("contextual_offer", [False, True])
async def test_semantic_followups_are_bounded_persisted_and_reused(database, contextual_offer):
    from prometeus.application.collect_market_evidence import CollectMarketEvidenceService
    from prometeus.application.decision_service import DecisionService
    from prometeus.application.plan_course_research import build_ecosystem_seed_calls
    from prometeus.application.qualify_market_evidence import EvidenceQualificationService
    from prometeus.domain.collection_execution import CollectionExecutionPolicy
    from prometeus.domain.configuration import load_tenant_config
    from prometeus.domain.research import CourseResearchPlan, CourseUnderstanding
    from prometeus.infrastructure.apify.registry import ApifyActorRegistry
    from prometeus.infrastructure.apify.schemas import ApifyExecutionResult, ApifyRunMetadata
    from prometeus.infrastructure.db.models import ResearchPlanModel
    from prometeus.infrastructure.jev.fake_client import FakeDecisionClient

    cfg = load_tenant_config(Path("config/tenants/ens.example.yaml"))
    ecosystem = cfg.ecosystem.model_copy(update={"competitors": [next(c for c in cfg.ecosystem.competitors if c.id == "fgv")], "sector_radar": []})
    settings = AppSettings(_env_file=None, APP_ENV="test", APIFY_ACTOR_GOOGLE_SEARCH="apify/google-search-scraper@0.0.474", APIFY_ACTOR_WEB_CRAWLER="apify/website-content-crawler@1.26.2")
    registry = ApifyActorRegistry.from_settings(settings)

    class EmptySearch:
        calls = []

        async def execute(self, call, *, max_total_charge_usd):
            self.calls.append(call.id)
            spec = registry.require(call.capability)
            return ApifyExecutionResult(run=ApifyRunMetadata(run_id=call.id, dataset_id=call.id,
                status="SUCCEEDED", actor_id=spec.actor_id, build_number=spec.build, cost_usd=0.001), items=[], total_items=0)

    async with database() as session:
        analysis = Analysis.create(tenant_id="ens", course_name="Governança de IA", correlation_id="test")
        analysis.start("test")
        await AnalysisRepository(session).save(analysis)
        await session.commit()
        understanding = CourseUnderstanding(analysis_id=analysis.id, course_title=analysis.course_name,
            subject_domains=["inteligência artificial", "governança"])
        questions, calls = build_ecosystem_seed_calls(understanding, ecosystem, ["google_search", "web_crawler"], None)
        plan = CourseResearchPlan(id="root-semantic", analysis_id=analysis.id, understanding_hash=understanding.snapshot_hash,
            tool_calls=calls, questions=questions, budget_limit_usd=None, execution_policy=CollectionExecutionPolicy())
        executor = EmptySearch()
        workflow = object.__new__(RunCourseAnalysis)
        workflow.session = session
        workflow.repository = AnalysisRepository(session)
        workflow.collector = CollectMarketEvidenceService(session, executor, registry)
        await workflow.collector.collect(tenant_id="ens", plan=plan)
        qualifier = EvidenceQualificationService(session, DecisionService(FakeDecisionClient(), session=session))
        if contextual_offer:
            from prometeus.infrastructure.db.models import MarketEvidenceModel

            session.add(MarketEvidenceModel(
                id="context-news", analysis_id=analysis.id, evidence_type="OFFER",
                source_name="apify_web_crawler", source_url="https://fgv.br/noticias/ia",
                collector="test", content_hash="context-news", title="Notícia institucional sobre IA",
                sanitized_data={"_qualification": {
                    "accepted": False, "context_only": True, "matched_actor_id": "fgv",
                    "actor_role": "configured_competitor",
                    "use_assessments": {"adjacent_competition": {"usable": True}},
                }},
            ))
            await session.commit()

            async def preserve_qualification(*args, **kwargs):
                return {"accepted": 0, "rejected": 1}

            qualifier = SimpleNamespace(qualify=preserve_qualification)
        helper = getattr(workflow, "_repair_competitor_queries", None)
        assert helper is not None, "Falta executar as variantes semânticas no workflow"
        _, result = await helper(analysis, understanding, ecosystem, {}, qualifier, "test", plan)
        assert result["searched_total"] == 1
        from prometeus.infrastructure.db.models import ToolRunModel
        validations = list((await session.execute(select(ToolRunModel).where(ToolRunModel.capability == "web_crawler"))).scalars())
        assert all(r.status == "EMPTY" and r.parameters.get("observation_status") == "no_candidates_to_validate" for r in validations)
        assert len(executor.calls) == 3
        snapshots = list((await session.execute(select(ResearchPlanModel))).scalars())
        assert len(snapshots) == 3
        assert {item.id for item in snapshots} == {"root-semantic", "root-semantic-competitor-v2", "root-semantic-competitor-v3"}
        await helper(analysis, understanding, ecosystem, {}, qualifier, "test", plan)
        assert len(executor.calls) == 3


def test_worker_schedules_retry_without_marking_failed_or_waiting(monkeypatch, tmp_path):
    from prometeus.workers import tasks

    url = f"sqlite+aiosqlite:///{tmp_path / 'worker_retry.sqlite3'}"
    due = datetime.now(UTC) + timedelta(minutes=5)

    async def setup():
        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            analysis = Analysis.create(tenant_id="ens", course_name="Coleta", correlation_id="test")
            analysis.start("test")
            await AnalysisRepository(session).save(analysis)
            session.add(AnalysisJobModel(analysis_id=analysis.id, correlation_id="test", status="PUBLISHED"))
            await session.commit()
            identifier = analysis.id
        await engine.dispose()
        return identifier

    identifier = asyncio.run(setup())

    async def collect(*args, **kwargs):
        raise CollectionRetryScheduled(due)

    monkeypatch.setattr(tasks, "settings", SimpleNamespace(DATABASE_URL=url))
    monkeypatch.setattr(tasks, "execute_workflow_steps", collect)
    assert tasks.run_analysis_workflow(identifier, "test")["status"] == "RETRY_SCHEDULED"

    async def check():
        engine = create_async_engine(url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            job = await session.get(AnalysisJobModel, identifier)
            assert job.status == "PENDING"
            assert job.next_attempt_at.replace(tzinfo=UTC) == due
            assert job.lease_token is None
            assert await session.scalar(select(AnalysisModel.status).where(AnalysisModel.id == identifier)) == "RUNNING"
        await engine.dispose()

    asyncio.run(check())
