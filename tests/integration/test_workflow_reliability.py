"""Regressões transacionais da auditoria A04–A07, somente banco temporário."""

from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.create_analysis import CreateAnalysisCommand, CreateAnalysisUseCase
from prometeus.application.decision_service import DecisionService
from prometeus.application.keywords import KeywordPipeline
from prometeus.application.run_course_analysis import RunCourseAnalysis
from prometeus.domain.analyses import Analysis, AnalysisStatus, DomainError
from prometeus.domain.configuration import AppSettings
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base, ExecutionEnvelopeModel
from prometeus.infrastructure.jev.fake_client import FakeDecisionClient


@pytest.fixture
async def database(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'reliability.sqlite3'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def test_stale_worker_cannot_overwrite_cancelled_status(database):
    async with database() as worker, database() as api:
        analysis = Analysis.create(tenant_id="ens", course_name="Test", correlation_id="test")
        analysis.start("test")
        await AnalysisRepository(worker).save(analysis)
        await worker.commit()
        cancelled = await AnalysisRepository(api).get_by_id(analysis.id)
        cancelled.cancel("cancel")
        await AnalysisRepository(api).save(cancelled)
        await api.commit()
        with pytest.raises(DomainError):
            await AnalysisRepository(worker).save(analysis)
        await worker.rollback()
        assert (
            await AnalysisRepository(worker).get_by_id(analysis.id)
        ).status == AnalysisStatus.CANCELLED


async def test_checkpoint_does_not_resurrect_cancellation_during_operation(database):
    async with database() as worker, database() as api:
        analysis = Analysis.create(tenant_id="ens", course_name="Test", correlation_id="test")
        analysis.start("test")
        await AnalysisRepository(worker).save(analysis)
        await worker.commit()
        workflow = object.__new__(RunCourseAnalysis)
        workflow.session = worker
        workflow.repository = AnalysisRepository(worker)

        async def operation():
            cancelled = await AnalysisRepository(api).get_by_id(analysis.id)
            cancelled.cancel("cancel")
            await AnalysisRepository(api).save(cancelled)
            await api.commit()
            return {"result": "preserved"}

        with pytest.raises(DomainError):
            await workflow._checkpoint(analysis, 1, operation)
        await worker.rollback()
        assert (
            await AnalysisRepository(worker).get_by_id(analysis.id)
        ).status == AnalysisStatus.CANCELLED


async def test_idempotency_is_institution_scoped_and_outbox_is_transactional(database):
    settings = AppSettings(_env_file=None, APP_ENV="test")
    async with database() as session:
        use_case = CreateAnalysisUseCase(session, settings)
        first = await use_case.execute(CreateAnalysisCommand("ens", "ENS", {}, "same", "test"))
        await session.commit()
        second = await use_case.execute(
            CreateAnalysisCommand("infnet", "Infnet", {}, "same", "test")
        )
        await session.commit()
        assert second.analysis_id != first.analysis_id
        table = Base.metadata.tables["analysis_jobs"]
        jobs = (await session.execute(select(table))).mappings().all()
        assert {job["analysis_id"] for job in jobs} == {first.analysis_id, second.analysis_id}


async def test_keywords_preserve_relevance_and_analysis_lineage(database):
    async def generate(**kwargs):
        return [f"seguros {number}" for number in range(15)]

    async with database() as session:
        analysis = Analysis.create(tenant_id="ens", course_name="Test", correlation_id="test")
        await AnalysisRepository(session).save(analysis)
        service = DecisionService(FakeDecisionClient(), session=session)
        result = await KeywordPipeline(
            SimpleNamespace(generate_keyword_candidates=generate), service
        ).build_keyword_set("Seguros", "Seguros", "Profissionais", analysis=analysis)
        await session.commit()
        assert all(
            candidate.relevance == "HIGH_RELEVANCE" for candidate in result.evaluated_candidates
        )
        envelopes = (await session.execute(select(ExecutionEnvelopeModel))).scalars().all()
        assert len(envelopes) == 15
        assert all(row.analysis_id == analysis.id and row.tenant_id == "ens" for row in envelopes)


async def test_keyword_provider_error_is_not_a_negative_judgment(database):
    async def generate(**kwargs):
        return ["seguros"]

    async with database() as session:
        service = DecisionService(FakeDecisionClient(simulate_unavailable=True), session=session)
        with pytest.raises(Exception, match="disponibilidade|indisponível"):
            await KeywordPipeline(
                SimpleNamespace(generate_keyword_candidates=generate), service
            ).build_keyword_set("Seguros", "Seguros", "Profissionais")


async def test_outbox_is_not_visible_until_creation_commits(database):
    from sqlalchemy import func

    from prometeus.infrastructure.db.models import AnalysisJobModel

    async with database() as writer, database() as reader:
        await CreateAnalysisUseCase(writer, AppSettings(_env_file=None, APP_ENV="test")).execute(
            CreateAnalysisCommand("ens", "ENS", {}, "visibility", "test")
        )
        assert await reader.scalar(select(func.count()).select_from(AnalysisJobModel)) == 0
        await reader.rollback()
        await writer.commit()
        assert await reader.scalar(select(func.count()).select_from(AnalysisJobModel)) == 1


async def test_failed_publication_is_reconciled_and_consumer_lease_is_exclusive(database):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import update

    from prometeus.application.analysis_jobs import (
        claim_analysis_job,
        publish_analysis_job,
        reconcile_analysis_jobs,
    )
    from prometeus.infrastructure.db.models import AnalysisJobModel

    async with database() as session:
        result = await CreateAnalysisUseCase(
            session, AppSettings(_env_file=None, APP_ENV="test")
        ).execute(CreateAnalysisCommand("ens", "ENS", {}, "retry", "test"))
        await session.commit()

        def unavailable(*args):
            raise ConnectionError("broker unavailable")

        assert await publish_analysis_job(session, result.analysis_id, unavailable) is False
        job = await session.get(AnalysisJobModel, result.analysis_id, populate_existing=True)
        assert job.status == "PENDING"
        assert job.last_error == "ConnectionError"
        await session.execute(
            update(AnalysisJobModel).values(
                next_attempt_at=datetime.now(UTC) - timedelta(seconds=1)
            )
        )
        await session.commit()
        calls = []
        assert await reconcile_analysis_jobs(session, lambda *args: calls.append(args)) == 1
        assert len(calls) == 1
        assert await claim_analysis_job(session, result.analysis_id, "worker-one") is True
        assert await claim_analysis_job(session, result.analysis_id, "worker-two") is False


async def test_apify_requests_abort_when_analysis_is_cancelled():
    import httpx

    from prometeus.infrastructure.apify.client import ApifyClient, ApifyTimeoutError

    calls = []

    def handler(request):
        calls.append((request.method, request.url.path))
        return httpx.Response(
            200, json={"data": {"id": "run-test", "status": "ABORTED", "usageTotalUsd": 0.02}}
        )

    async def cancelled():
        return False

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        apify = ApifyClient(
            api_token="test",
            registry=SimpleNamespace(),
            http_client=http,
            cancellation_check=cancelled,
        )
        with pytest.raises(ApifyTimeoutError) as captured:
            await apify._wait_for_terminal({"id": "run-test", "status": "RUNNING"})
        assert captured.value.run_data["status"] == "ABORTED"
        assert calls == [("POST", "/v2/actor-runs/run-test/abort")]


async def test_reconciler_does_not_starve_pending_jobs_behind_active_leases(database):
    from datetime import UTC, datetime, timedelta

    from prometeus.application.analysis_jobs import reconcile_analysis_jobs
    from prometeus.infrastructure.db.models import AnalysisJobModel

    now = datetime.now(UTC)
    async with database() as session:
        for number in range(101):
            analysis = Analysis.create(
                tenant_id="ens", course_name="Lease fixture", correlation_id="test"
            )
            await AnalysisRepository(session).save(analysis)
            session.add(
                AnalysisJobModel(
                    analysis_id=analysis.id,
                    correlation_id="test",
                    status="RUNNING",
                    lease_token=f"active-{number}",
                    lease_expires_at=now + timedelta(hours=1),
                    next_attempt_at=now - timedelta(hours=1),
                )
            )
        pending = Analysis.create(
            tenant_id="ens", course_name="Pending fixture", correlation_id="test"
        )
        await AnalysisRepository(session).save(pending)
        session.add(
            AnalysisJobModel(
                analysis_id=pending.id,
                correlation_id="test",
                status="PENDING",
                next_attempt_at=now - timedelta(seconds=1),
            )
        )
        await session.commit()
        published = []
        assert (
            await reconcile_analysis_jobs(
                session, lambda identifier, *_: published.append(identifier)
            )
            == 1
        )
        assert published == [pending.id]


async def test_lost_execution_lease_stops_before_checkpoint_operation(database):
    from prometeus.domain.analyses import WorkflowStoppedError

    async with database() as session:
        analysis = Analysis.create(tenant_id="ens", course_name="Lease", correlation_id="test")
        analysis.start("test")
        await AnalysisRepository(session).save(analysis)
        await session.commit()
        workflow = object.__new__(RunCourseAnalysis)
        workflow.session = session
        workflow.repository = AnalysisRepository(session)

        async def lost():
            raise WorkflowStoppedError("Lease perdido")

        workflow.execution_guard = lost
        called = []

        async def operation():
            called.append(True)
            return {}

        with pytest.raises(WorkflowStoppedError):
            await workflow._checkpoint(analysis, 1, operation)
        assert called == []
