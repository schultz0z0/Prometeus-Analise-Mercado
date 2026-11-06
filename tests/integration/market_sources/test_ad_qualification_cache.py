from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application import qualify_market_evidence as qualification
from prometeus.application.decision_service import DecisionService
from prometeus.domain.analyses import Analysis
from prometeus.domain.research import CourseUnderstanding
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base, MarketEvidenceModel
from prometeus.infrastructure.jev.fake_client import FakeDecisionClient


async def test_ad_projection_upgrade_rejudges_ads_and_preserves_unaffected_job_cache(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    class RecordingModel(FakeDecisionClient):
        calls = []

        async def execute_choice(self, pack, context, evidence_ids=None):
            self.calls.append(evidence_ids)
            if evidence_ids == ["ad"]:
                assert (
                    context["untrusted_evidence"]["ad_copy"] == "Curso de governança e privacidade."
                )
            return await super().execute_choice(pack, context, evidence_ids)

    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        analysis = Analysis.create(
            tenant_id="ens", course_name="Governança de IA", correlation_id="ad-cache"
        )
        await AnalysisRepository(session).save(analysis)
        for identifier, kind, source, payload in [
            (
                "ad",
                "PAID_COMPETITION",
                "apify_meta_ads_library",
                {
                    "ad_archive_id": "123",
                    "snapshot": {"body": {"text": "Curso de governança e privacidade."}},
                },
            ),
            (
                "job",
                "JOB_MARKET",
                "apify_linkedin_jobs",
                {"title": "Analista de governança", "location": "São Paulo, Brazil"},
            ),
        ]:
            session.add(
                MarketEvidenceModel(
                    id=identifier,
                    analysis_id=analysis.id,
                    evidence_type=kind,
                    source_name=source,
                    source_url=f"https://example.org/{identifier}",
                    title=identifier,
                    collector="test",
                    content_hash=identifier,
                    sanitized_data=payload,
                    raw_payload=payload,
                )
            )
        await session.commit()
        model = RecordingModel(canned_choices={"market-relevance-v1": "RELEVANT"})
        service = qualification.EvidenceQualificationService(
            session, DecisionService(model, session)
        )
        understanding = CourseUnderstanding(
            analysis_id=analysis.id, course_title=analysis.course_name
        )
        monkeypatch.setattr(qualification, "AD_PROJECTOR_VERSION", "ad-projection-legacy")
        await service.qualify(analysis, understanding, "ad-cache")
        job = await session.get(MarketEvidenceModel, "job")
        original_job_decision = job.sanitized_data["_qualification"]["decision_id"]
        model.calls.clear()
        monkeypatch.setattr(qualification, "AD_PROJECTOR_VERSION", "ad-projection-v2")
        await service.qualify(analysis, understanding, "ad-cache")
        assert model.calls == [["ad"]]
        assert job.sanitized_data["_qualification"]["decision_id"] == original_job_decision
        ad = await session.get(MarketEvidenceModel, "ad")
        assert (
            ad.sanitized_data["_qualification"]["component_versions"]["ad_projector"]
            == "ad-projection-v2"
        )
        model.calls.clear()
        await service.qualify(analysis, understanding, "ad-cache")
        assert model.calls == []
    await engine.dispose()
