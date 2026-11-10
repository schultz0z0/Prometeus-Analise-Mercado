import copy
import hashlib
import json
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.decision_service import DecisionService
from prometeus.application.integral_evidence_reader import (
    IntegralEvidenceReader,
    IntegralEvidenceReadingError,
)
from prometeus.application.qualify_market_evidence import EvidenceQualificationService
from prometeus.domain.analyses import Analysis
from prometeus.domain.research import CourseUnderstanding
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import (
    Base,
    MarketEvidenceModel,
    ResearchPlanModel,
    ToolRunAttemptModel,
    ToolRunModel,
)
from prometeus.infrastructure.jev.fake_client import FakeDecisionClient


class ReadingModel:
    model = "test-integral-qualification"

    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    async def generate_structured(self, prompt, *, schema, system_prompt=None):
        self.calls.append(json.loads(prompt))
        if self.fail:
            raise ConnectionError("unavailable")
        part = self.calls[-1]["untrusted_part"]
        return json.dumps(
            {
                "part_id": part["part_id"],
                "observations": [
                    {
                        "fragment_id": fragment["fragment_id"],
                        "disposition": "CONTEXT",
                        "analysis": "Trecho preservado para interpretação da pertinência.",
                        "quotes": [fragment["text"]] if fragment["text"] else [],
                    }
                    for fragment in part["fragments"]
                ],
            }
        )


class CapturingDecisions(DecisionService):
    def __init__(self, db):
        super().__init__(FakeDecisionClient(canned_choices={"market-relevance-v1": "CONTEXT"}), db)
        self.contexts = []

    async def execute_judgment(self, **kwargs):
        self.contexts.append(copy.deepcopy(kwargs["context"]))
        return await super().execute_judgment(**kwargs)


@pytest.mark.asyncio
@pytest.mark.parametrize("fail", [False, True])
async def test_integral_reading_precedes_qualification_and_preserves_progress(fail):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        analysis = Analysis.create(tenant_id="ens", course_name="Governança IA", correlation_id="r")
        await AnalysisRepository(db).save(analysis)
        payload = {"unknown": "informação " * 400 + "CONTRAPROVA FINAL", "nested": {"v": 0}}
        row = MarketEvidenceModel(
            id="read-one",
            analysis_id=analysis.id,
            evidence_type="SOCIAL_VOICE",
            source_name="test",
            source_url="https://example.com",
            collector="test",
            content_hash="hash",
            title="Observação",
            raw_payload=payload,
            sanitized_data=payload,
            quality_score=1,
            cost_usd=0,
        )
        db.add(row)
        await db.commit()
        model = ReadingModel(fail=fail)
        decisions = CapturingDecisions(db)
        service = EvidenceQualificationService(
            db, decisions, reader=IntegralEvidenceReader(model, chunk_budget=3000)
        )
        understanding = CourseUnderstanding(
            analysis_id=analysis.id, course_title=analysis.course_name
        )
        if fail:
            with pytest.raises(IntegralEvidenceReadingError):
                await service.qualify(analysis, understanding, "r")
            assert not decisions.contexts
            assert not row.sanitized_data["_reading"]["complete"]
        else:
            await service.qualify(analysis, understanding, "r")
            assert row.sanitized_data["_reading"]["complete"]
            context = decisions.contexts[0]["untrusted_integral_reading"]
            assert "CONTRAPROVA FINAL" in json.dumps(context, ensure_ascii=False)
            before = len(model.calls)
            await service.qualify(analysis, understanding, "r")
            assert len(model.calls) == before
            assert len(decisions.contexts) == 1
            assert all("_reading" not in json.dumps(call["untrusted_part"]) for call in model.calls)
    await engine.dispose()


@pytest.mark.asyncio
async def test_qualification_receives_exclusive_parent_archive_context_from_correct_provider_run():
    def archive(run_id, data):
        def sha(value):
            return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

        return {
            "schema_version": 1,
            "provider_run_id": run_id,
            "dataset_id": "dataset-" + run_id,
            "source_sha256": sha(data),
            "retrieval_complete": True,
            "dataset_total_items": len(data),
            "items_read": len(data),
            "total_items_source": "provider_pagination",
            "items": [
                {"index": i, "source_sha256": sha(item), "sanitized_data": item}
                for i, item in enumerate(data)
            ],
        }

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        analysis = Analysis.create(tenant_id="ens", course_name="Governança IA", correlation_id="r")
        await AnalysisRepository(db).save(analysis)
        db.add(
            ResearchPlanModel(id="plan", analysis_id=analysis.id, tenant_id="ens", cache_key="key")
        )
        payload = {
            "title": "Curso de Governança IA",
            "url": "https://school.test/course",
            "_source_record": {"index": 0},
        }
        current = archive(
            "current",
            [
                {
                    "organicResults": [payload],
                    "paidResults": [{"text": "EXCLUSIVE PARENT COUNTEREVIDENCE"}],
                }
            ],
        )
        old = archive("old", [{"text": "OLD_RUN_DO_NOT_ATTRIBUTE"}])
        run = ToolRunModel(
            id="run",
            analysis_id=analysis.id,
            research_plan_id="plan",
            planned_call_id="call",
            capability="google_search",
            query="Governança IA",
            actor_id="actor",
            actor_build="1",
            status="SUCCEEDED",
            provider_run_id="current",
            dataset_id="dataset-current",
            parameters={"dataset_archive": current, "prior_dataset_archives": [old]},
        )
        db.add(run)
        db.add(
            ToolRunAttemptModel(
                id="attempt",
                tool_run_id="run",
                analysis_id=analysis.id,
                tenant_id="ens",
                task_key="task",
                attempt_index=1,
                input_hash="hash",
                actor_id="actor",
                actor_build="1",
                status="SUCCEEDED",
                provider_run_id="current",
                dataset_id="dataset-current",
                started_at=datetime.now(UTC),
            )
        )
        db.add(
            MarketEvidenceModel(
                id="evidence",
                analysis_id=analysis.id,
                tool_run_id="run",
                tool_run_attempt_id="attempt",
                evidence_type="OFFER",
                source_name="apify_google_search",
                source_url=payload["url"],
                collector="test",
                content_hash="hash",
                title=payload["title"],
                raw_payload=payload,
                sanitized_data=payload,
                quality_score=1,
                cost_usd=0,
            )
        )
        await db.commit()
        decisions = CapturingDecisions(db)
        service = EvidenceQualificationService(
            db, decisions, reader=IntegralEvidenceReader(ReadingModel())
        )
        await service.qualify(
            analysis,
            CourseUnderstanding(analysis_id=analysis.id, course_title=analysis.course_name),
            "r",
        )
        context = decisions.contexts[0]["untrusted_archive_reading"]
        serialized = json.dumps(context)
        assert "EXCLUSIVE PARENT COUNTEREVIDENCE" in serialized
        assert "OLD_RUN_DO_NOT_ATTRIBUTE" not in serialized
        assert context["records"][0]["relationship"] == "source_parent"
        assert context["records"][0]["provider_run_id"] == "current"
    await engine.dispose()
