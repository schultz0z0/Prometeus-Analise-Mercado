import hashlib
import json
from copy import deepcopy

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.evidence_reading_context import (
    archive_analysis_context,
    evidence_archive_context,
)
from prometeus.application.integral_evidence_reader import (
    IntegralEvidenceReader,
    IntegralEvidenceReadingError,
)
from prometeus.application.read_collected_datasets import DatasetReadingService
from prometeus.infrastructure.db.models import (
    AnalysisModel,
    Base,
    ResearchPlanModel,
    ToolRunModel,
)


class RecordingModel:
    model = "archive-test"

    def __init__(self, fail_on=None):
        self.calls = []
        self.fail_on = fail_on

    async def generate_structured(self, prompt, *, schema, system_prompt=None):
        self.calls.append(json.loads(prompt))
        if len(self.calls) == self.fail_on:
            raise ConnectionError("provider unavailable")
        part = self.calls[-1]["untrusted_part"]
        return json.dumps(
            {
                "part_id": part["part_id"],
                "observations": [
                    {
                        "fragment_id": f["fragment_id"],
                        "disposition": "CONTEXT",
                        "analysis": "Observação contextual da fonte.",
                        "quotes": [f["text"]] if f["text"] else [],
                    }
                    for f in part["fragments"]
                ],
            }
        )


def archive(run_id, data, *, complete=True, total=None):
    def sha(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

    return {
        "schema_version": 1,
        "provider_run_id": run_id,
        "dataset_id": "dataset-" + run_id,
        "source_sha256": sha(data),
        "retrieval_complete": complete,
        "dataset_total_items": len(data) if total is None else total,
        "items_read": len(data),
        "total_items_source": "provider_pagination",
        "items": [
            {
                "index": index,
                "source_sha256": sha(item),
                "sanitized_data": item,
                "raw_payload": {"secret": "RAW_SECRET_MUST_NOT_ENTER_MODEL"},
                "sanitization_changed": True,
            }
            for index, item in enumerate(data)
        ],
    }


@pytest_asyncio.fixture
async def sessions():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def seed(session, analysis_id, *, current=None, previous=None):
    session.add(AnalysisModel(id=analysis_id, tenant_id=analysis_id, course_name="Curso"))
    session.add(
        ResearchPlanModel(
            id="plan-" + analysis_id,
            analysis_id=analysis_id,
            tenant_id=analysis_id,
            cache_key=analysis_id,
        )
    )
    run = ToolRunModel(
        id="tool-" + analysis_id,
        analysis_id=analysis_id,
        research_plan_id="plan-" + analysis_id,
        planned_call_id="call",
        capability="google_search",
        query="Curso",
        actor_id="actor/test",
        actor_build="1",
        provider_run_id="current",
        dataset_id="dataset-current",
        status="SUCCEEDED",
        parameters={"unrelated": "preserved", "prior_dataset_archives": previous or []},
    )
    if current is not None:
        run.parameters = {**run.parameters, "dataset_archive": current}
    session.add(run)
    await session.commit()
    return run


@pytest.mark.asyncio
async def test_prior_failed_run_keeps_its_own_status_when_logical_task_later_succeeds(sessions):
    old = {**archive("old", [{"text": "captura parcial"}]), "provider_status": "FAILED"}
    current = {**archive("current", [{"text": "captura atual"}]), "provider_status": "SUCCEEDED"}
    async with sessions() as session:
        await seed(session, "ours", current=current, previous=[old])
        model = RecordingModel()
        await DatasetReadingService(session, IntegralEvidenceReader(model)).read(
            "ours", course_context={}
        )
        contexts = [call["source_context"] for call in model.calls]
        assert contexts[0]["run_status"] == "FAILED"
        assert contexts[1]["run_status"] == "SUCCEEDED"


@pytest.mark.asyncio
@pytest.mark.parametrize("mismatch", ["run_id", "dataset_id"])
async def test_old_archive_cannot_cover_the_current_provider_run(sessions, mismatch):
    current = archive("current", [{"text": "archive from a different remote output"}])
    if mismatch == "run_id":
        current["provider_run_id"] = "old"
    else:
        current["dataset_id"] = "old-dataset"
    async with sessions() as session:
        await seed(session, "ours", current=current)
        result = await DatasetReadingService(
            session, IntegralEvidenceReader(RecordingModel())
        ).read("ours", course_context={})
        assert not result["complete"]
        assert any("current_remote_archive_missing" in file["issues"] for file in result["files"])


@pytest.mark.asyncio
async def test_archive_context_retains_all_interpretations_and_lineage_without_raw_payload(
    sessions,
):
    old = archive("old", [{"error": "diagnostic from failed run without evidence"}])
    old["provider_status"] = "FAILED"
    parent = {
        "organicResults": [{"title": "Course"}],
        "paidResults": [{"text": "EXCLUSIVE PARENT COUNTEREVIDENCE"}],
    }
    current = archive("current", [parent, {"diagnostic": "unmatched record"}])

    class TechnicalModel(RecordingModel):
        async def generate_structured(self, *args, **kwargs):
            result = json.loads(await super().generate_structured(*args, **kwargs))
            for observation in result["observations"]:
                observation.update(disposition="TECHNICAL", quotes=[])
            return json.dumps(result)

    async with sessions() as session:
        run = await seed(session, "ours", current=current, previous=[old])
        await DatasetReadingService(session, IntegralEvidenceReader(TechnicalModel())).read(
            "ours", course_context={}
        )
        context = archive_analysis_context(run.parameters, tool_run_id=run.id)
        assert context["complete"] is True
        assert len(context["records"]) == 3
        assert context["records"][0]["run_status"] == "FAILED"
        assert context["records"][0]["reading"]["observations"][0]["quotes"] == []
        assert "RAW_SECRET" not in json.dumps(context)
        matching = evidence_archive_context(
            run.parameters,
            tool_run_id=run.id,
            normalized_data={"title": "Course", "_source_record": {"index": 0}},
            provider_run_id="current",
            dataset_id="dataset-current",
        )
        assert len(matching["records"]) == 2
        assert [record["relationship"] for record in matching["records"]] == [
            "source_parent",
            "same_provider_run_context",
        ]
        assert all(record["provider_run_id"] == "current" for record in matching["records"])
        stale = deepcopy(run.parameters)
        stale["dataset_archive"]["items"][0]["sanitized_data"]["changed"] = True
        assert archive_analysis_context(stale, tool_run_id=run.id)["complete"] is False


@pytest.mark.asyncio
async def test_reads_all_archives_duplicates_unknown_fields_and_scopes_analysis(sessions):
    old = archive("old", [{"unknown": "old-data"}])
    current = archive("current", [{"unknown": "new-data"}] * 2)
    async with sessions() as session:
        await seed(session, "ours", current=current, previous=[old])
        await seed(session, "other", current=archive("other", [{"private": "OTHER_TENANT"}]))
        model = RecordingModel()
        result = await DatasetReadingService(session, IntegralEvidenceReader(model)).read(
            "ours",
            course_context={"title": "Curso"},
        )
        assert result["complete"]
        assert (result["files_total"], result["files_complete"]) == (2, 2)
        assert (result["items_total"], result["items_complete"], result["items_pending"]) == (
            3,
            3,
            0,
        )
        assert len(model.calls) == 3
        delivered = json.dumps(model.calls)
        assert "old-data" in delivered and "new-data" in delivered
        assert "RAW_SECRET" not in delivered and "OTHER_TENANT" not in delivered
        keys = [item["reading_key"] for file in result["files"] for item in file["items"]]
        assert len(set(keys)) == 3
        assert result["files"][0]["findings"][0]["provider_run_id"] == "old"
        assert result["files"][1]["findings"][0]["item_index"] == 0
    async with sessions() as session:
        ours = await session.get(ToolRunModel, "tool-ours")
        other = await session.get(ToolRunModel, "tool-other")
        assert len(ours.parameters["dataset_readings"]) == 3
        assert ours.parameters["unrelated"] == "preserved"
        assert ours.parameters["dataset_archive"] == current
        assert "dataset_readings" not in other.parameters


@pytest.mark.asyncio
async def test_committed_parts_resume_after_failure_and_model_change_invalidates_cache(sessions):
    current = archive("current", [{"body": "evidência " * 800}])
    first = RecordingModel(fail_on=2)
    async with sessions() as session:
        await seed(session, "ours", current=current)
        with pytest.raises(IntegralEvidenceReadingError):
            await DatasetReadingService(
                session,
                IntegralEvidenceReader(first, chunk_budget=2200),
            ).read("ours", course_context={"title": "Curso"})
    async with sessions() as session:
        run = await session.get(ToolRunModel, "tool-ours")
        state = next(iter(run.parameters["dataset_readings"].values()))
        assert not state["complete"] and state["status"] == "INCOMPLETE"
        assert state["manifest"]["completed_parts"] == 1
        total = state["manifest"]["total_parts"]
        resumed = RecordingModel()
        service = DatasetReadingService(session, IntegralEvidenceReader(resumed, chunk_budget=2200))
        result = await service.read("ours", course_context={"title": "Curso"})
        assert result["complete"] and len(resumed.calls) == total - 1
        await service.read("ours", course_context={"title": "Curso"})
        assert len(resumed.calls) == total - 1
        changed = RecordingModel()
        await DatasetReadingService(
            session,
            IntegralEvidenceReader(
                changed,
                chunk_budget=2200,
                model_identity="new-model",
            ),
        ).read("ours", course_context={"title": "Curso"})
        assert len(changed.calls) == total


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mutation", ["partial", "wrong_count", "duplicate_index", "unverified", "schema"]
)
async def test_inconsistent_retrieval_never_claims_integral_delivery(sessions, mutation):
    current = archive("current", [{"a": "one"}, {"a": "two"}])
    if mutation == "partial":
        current["retrieval_complete"] = False
    elif mutation == "wrong_count":
        current["dataset_total_items"] = 3
    elif mutation == "duplicate_index":
        current["items"][1]["index"] = 0
    elif mutation == "unverified":
        current["total_items_source"] = "unverified"
    else:
        current["schema_version"] = 999
    async with sessions() as session:
        await seed(session, "ours", current=current)
        model = RecordingModel()
        result = await DatasetReadingService(session, IntegralEvidenceReader(model)).read(
            "ours",
            course_context={},
        )
        assert not result["complete"] and not result["files"][0]["complete"]
        assert result["files"][0]["issues"]
        assert result["items_complete"] == 2
        assert len(model.calls) == 2


@pytest.mark.asyncio
async def test_missing_sanitized_data_does_not_fall_back_to_private_payload(sessions):
    current = archive("current", [{"a": "one"}])
    del current["items"][0]["sanitized_data"]
    async with sessions() as session:
        await seed(session, "ours", current=current)
        model = RecordingModel()
        result = await DatasetReadingService(session, IntegralEvidenceReader(model)).read(
            "ours",
            course_context={},
        )
        assert not result["complete"] and result["items_pending"] == 1
        assert result["files"][0]["items"][0]["error"] == "missing_sanitized_data"
        assert not model.calls


@pytest.mark.asyncio
async def test_verified_empty_archive_complete_but_missing_archive_and_no_runs_pending(sessions):
    async with sessions() as session:
        await seed(session, "empty", current=archive("current", []))
        await seed(session, "missing")
        session.add(AnalysisModel(id="no-runs", tenant_id="none", course_name="Curso"))
        await session.commit()
        model = RecordingModel()
        service = DatasetReadingService(session, IntegralEvidenceReader(model))
        assert (await service.read("empty", course_context={}))["complete"]
        assert not (await service.read("missing", course_context={}))["complete"]
        assert not (await service.read("no-runs", course_context={}))["complete"]
        assert not model.calls


@pytest.mark.asyncio
async def test_execution_guard_blocks_llm_and_all_checkpoint_mutations(sessions):
    async with sessions() as session:
        run = await seed(session, "ours", current=archive("current", [{"a": "one"}]))
        before = deepcopy(run.parameters)
        model = RecordingModel()

        async def guard():
            raise RuntimeError("lease lost")

        with pytest.raises(RuntimeError, match="lease lost"):
            await DatasetReadingService(session, IntegralEvidenceReader(model)).read(
                "ours",
                course_context={},
                execution_guard=guard,
            )
        assert not model.calls and run.parameters == before


@pytest.mark.asyncio
async def test_prior_archives_do_not_hide_missing_current_archive(sessions):
    async with sessions() as session:
        await seed(session, "ours", previous=[archive("old", [{"a": "old"}])])
        result = await DatasetReadingService(
            session, IntegralEvidenceReader(RecordingModel())
        ).read(
            "ours",
            course_context={},
        )
        assert not result["complete"]
        assert result["files_total"] == 2 and result["files_complete"] == 1


@pytest.mark.asyncio
async def test_lease_loss_after_llm_propagates_original_error_without_new_checkpoint(sessions):
    class LeaseLost(RuntimeError):
        pass

    async with sessions() as session:
        run = await seed(session, "ours", current=archive("current", [{"a": "one"}]))
        model = RecordingModel()
        calls = 0

        async def guard():
            nonlocal calls
            calls += 1
            if calls == 5:
                raise LeaseLost("lease lost after provider response")

        with pytest.raises(LeaseLost):
            await DatasetReadingService(session, IntegralEvidenceReader(model)).read(
                "ours",
                course_context={},
                execution_guard=guard,
            )
        assert len(model.calls) == 1
        state = next(iter(run.parameters["dataset_readings"].values()))
        assert not state["complete"] and state["manifest"]["completed_parts"] == 0


@pytest.mark.asyncio
async def test_multiple_runs_survive_expire_on_commit(sessions):
    async with sessions() as session:
        await seed(session, "ours", current=archive("current", [{"a": "one"}]))
        session.add(
            ToolRunModel(
                id="second-tool",
                analysis_id="ours",
                research_plan_id="plan-ours",
                planned_call_id="second",
                capability="google_search",
                query="Curso",
                actor_id="actor/test",
                actor_build="1",
                status="SUCCEEDED",
                parameters={"dataset_archive": archive("second", [{"b": "two"}])},
            )
        )
        await session.commit()
    expiring = async_sessionmaker(sessions.kw["bind"], expire_on_commit=True)
    async with expiring() as session:
        result = await DatasetReadingService(
            session, IntegralEvidenceReader(RecordingModel())
        ).read(
            "ours",
            course_context={},
        )
        assert result["complete"] and result["items_complete"] == 2


@pytest.mark.asyncio
async def test_failed_before_remote_execution_is_reported_without_blocking_existing_data(sessions):
    async with sessions() as session:
        await seed(session, "ours", current=archive("current", [{"a": "one"}]))
        session.add(
            ToolRunModel(
                id="failed-tool",
                analysis_id="ours",
                research_plan_id="plan-ours",
                planned_call_id="failed",
                capability="google_search",
                query="Curso",
                actor_id="actor/test",
                actor_build="1",
                status="FAILED",
                error_code="LOCAL_VALIDATION_FAILED",
                parameters={},
            )
        )
        await session.commit()
        result = await DatasetReadingService(
            session, IntegralEvidenceReader(RecordingModel())
        ).read(
            "ours",
            course_context={},
        )
        assert result["complete"] and result["files_total"] == 1
        assert result["tool_runs_total"] == 2 and result["remote_runs_total"] == 1
        assert result["runs_without_dataset"][0]["tool_run_id"] == "failed-tool"
        assert result["runs_without_dataset"][0]["run_status"] == "FAILED"
