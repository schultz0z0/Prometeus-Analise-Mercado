import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.decision_service import DecisionService
from prometeus.application.qualify_market_evidence import EvidenceQualificationService
from prometeus.domain.analyses import Analysis
from prometeus.domain.research import CourseUnderstanding
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base, MarketEvidenceModel
from prometeus.infrastructure.jev.fake_client import FakeDecisionClient


@pytest.mark.parametrize("choice", ["RELEVANT", "CONTEXT"])
async def test_competition_assessments_are_exclusive_and_news_never_counts(choice):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        analysis = Analysis.create(tenant_id="ens", course_name="MBA em Governança de IA", correlation_id="compare")
        await AnalysisRepository(session).save(analysis)
        for identifier, title, category, path in [
            ("direct", "MBA em Governança de IA", "MBA", "/cursos/mba"),
            ("adjacent", "Extensão em Governança de IA", "Extensão", "/cursos/extensao"),
            ("unknown", "Governança de IA", "", "/cursos/ia"),
            ("news", "MBA em Governança de IA", "MBA", "/noticias/novo-mba"),
        ]:
            data = {"title": title, "course_name": title, "category": category}
            session.add(MarketEvidenceModel(
                id=identifier, analysis_id=analysis.id, evidence_type="OFFER", source_name="apify_web_crawler",
                source_url=f"https://escola.br{path}", collector="test", content_hash=identifier,
                title=title, sanitized_data=data, raw_payload=data,
            ))
        await session.commit()
        ad_data = {"pageName": "Ibmec", "headline": "MBA em Governança de IA", "text": "Inscreva-se", "cta_url": "https://pos.ibmec.br/cursos/mba-ia"}
        session.add(MarketEvidenceModel(
            id="ad", analysis_id=analysis.id, evidence_type="PAID_COMPETITION", source_name="apify_meta_ads_library",
            source_url="https://facebook.com/ads/library/?id=123", collector="test", content_hash="ad",
            title="Ibmec", sanitized_data=ad_data, raw_payload=ad_data,
        ))
        await session.commit()
        service = EvidenceQualificationService(session, DecisionService(FakeDecisionClient(canned_choices={"market-relevance-v1": choice}), session))
        understanding = CourseUnderstanding(analysis_id=analysis.id, course_title=analysis.course_name, level="MBA")
        await service.qualify(analysis, understanding, "compare")
        for identifier, relation in [("direct", "direct"), ("adjacent", "adjacent"), ("unknown", "unclassified"), ("news", "not_qualified")]:
            if choice == "CONTEXT" and identifier != "adjacent":
                relation = "not_qualified"
            row = await session.get(MarketEvidenceModel, identifier)
            q = row.sanitized_data["_qualification"]
            assert q["offer_comparability"]["relation"] == relation
            uses = q["use_assessments"]
            assert uses["direct_competition"]["usable"] is (relation == "direct")
            assert uses["adjacent_competition"]["usable"] is (relation == "adjacent")
            assert q["accepted"] is (relation != "not_qualified")
            if relation != "not_qualified":
                assert q["context_only"] is False
                assert "competitive_offers" in q["use_for"]
        ad = await session.get(MarketEvidenceModel, "ad")
        q = ad.sanitized_data["_qualification"]
        assert q["accepted"] is (choice == "RELEVANT")
        assert ("paid_competition" in q["use_for"]) is (choice == "RELEVANT")
        assert q["offer_comparability"]["is_offer"] is False
    await engine.dispose()
