from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.application.decision_service import DecisionService
from prometeus.domain.analyses import Analysis
from prometeus.domain.research import CourseUnderstanding
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base, MarketEvidenceModel
from prometeus.infrastructure.jev.fake_client import FakeDecisionClient


async def test_irrelevant_ad_and_out_of_scope_job_are_not_counted_and_retry_reuses_judgment():
    from prometeus.application.qualify_market_evidence import EvidenceQualificationService

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as db:
        analysis = Analysis.create(tenant_id="ens", course_name="MBA Seguros", correlation_id="q")
        await AnalysisRepository(db).save(analysis)
        for name, kind, payload in [
            (
                "ad",
                "PAID_COMPETITION",
                {"text": "Advogado para indenização", "_qualification": {"accepted": True}},
            ),
            ("us", "JOB_MARKET", {"title": "Attorney", "location": "Irving, TX"}),
        ]:
            db.add(
                MarketEvidenceModel(
                    id=name,
                    analysis_id=analysis.id,
                    evidence_type=kind,
                    source_name="test",
                    source_url=f"https://example.com/{name}",
                    collector="test",
                    content_hash=name,
                    title=name,
                    raw_payload=payload,
                    sanitized_data=payload,
                    quality_score=1,
                    cost_usd=0,
                )
            )
        await db.commit()
        model = FakeDecisionClient(canned_choices={"market-relevance-v1": "IRRELEVANT"})
        service = EvidenceQualificationService(db, DecisionService(model, db))
        understanding = CourseUnderstanding(
            analysis_id=analysis.id, course_title=analysis.course_name
        )
        first = await service.qualify(analysis, understanding, "q")
        second = await service.qualify(analysis, understanding, "q")
        assert first["accepted"] == 0
        assert first["rejected"] == 2
        assert second == first
        row = await db.get(MarketEvidenceModel, "ad")
        assert row.sanitized_data["_qualification"]["accepted"] is False
        assert row.sanitized_data["_qualification"]["decision_id"]
        # Uma política antiga não pode conservar aceitação incompatível com
        # a política atual só por ter o mesmo hash de entendimento.
        old = dict(row.sanitized_data)
        old["_qualification"] = {
            **old["_qualification"],
            "qualification_version": 1,
            "accepted": True,
        }
        row.sanitized_data = old
        await db.commit()
        await service.qualify(analysis, understanding, "policy-refresh")
        assert row.sanitized_data["_qualification"]["accepted"] is False
        assert row.sanitized_data["_qualification"]["qualification_version"] == 3
        assert row.sanitized_data["_qualification"]["pack_hash"]
        prior_decision = row.sanitized_data["_qualification"]["decision_id"]
        pack = service.decisions.get_pack("market-relevance-v1")
        service.decisions._packs_cache["market-relevance-v1"] = pack.model_copy(
            update={"version": "99.0.0"}
        )
        await service.qualify(analysis, understanding, "pack-refresh")
        assert row.sanitized_data["_qualification"]["decision_id"] != prior_decision
    await engine.dispose()


async def test_own_ad_is_context_while_pertinent_job_survives_descriptive_brazil_scope():
    from prometeus.application.qualify_market_evidence import EvidenceQualificationService

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        analysis = Analysis.create(
            tenant_id="ens", course_name="MBA Seguros", correlation_id="uses"
        )
        await AnalysisRepository(db).save(analysis)
        for name, kind, payload in [
            (
                "own",
                "PAID_COMPETITION",
                {"pageName": "Escola de Negócios e Seguros", "text": "MBA gestão de seguros"},
            ),
            (
                "job",
                "JOB_MARKET",
                {
                    "id": "4481932467",
                    "title": "Gerente de seguros",
                    "location": "São Paulo, Brazil",
                    "description": "Gerenciar sinistros, subscrição e resseguros.",
                },
            ),
        ]:
            db.add(
                MarketEvidenceModel(
                    id=name,
                    analysis_id=analysis.id,
                    evidence_type=kind,
                    source_name="test",
                    source_url=f"https://example.com/{name}",
                    collector="test",
                    content_hash=name,
                    title=name,
                    raw_payload=payload,
                    sanitized_data=payload,
                    quality_score=1,
                    cost_usd=0,
                )
            )
        await db.commit()
        service = EvidenceQualificationService(
            db,
            DecisionService(
                FakeDecisionClient(canned_choices={"market-relevance-v1": "RELEVANT"}), db
            ),
        )
        understanding = CourseUnderstanding(
            analysis_id=analysis.id,
            course_title=analysis.course_name,
            geography="Brasil como contexto do programa e do mercado estudado; participação online de qualquer localidade.",
        )
        outcome = await service.qualify(
            analysis,
            understanding,
            "uses",
            institution_context={"name": "Escola de Negócios e Seguros"},
        )
        assert outcome["accepted"] == 1
        own = await db.get(MarketEvidenceModel, "own")
        job = await db.get(MarketEvidenceModel, "job")
        assert own.sanitized_data["_qualification"]["accepted"] is False
        assert own.sanitized_data["_qualification"]["context_only"] is True
        assert own.sanitized_data["_qualification"]["exclusion_codes"] == ["own_institution"]
        assert "employability" in job.sanitized_data["_qualification"]["use_for"]
        assert "curriculum" in job.sanitized_data["_qualification"]["use_for"]
        service.decisions.decision_model.canned_choices["market-relevance-v1"] = "CONTEXT"
        pack = service.decisions.get_pack("market-relevance-v1")
        service.decisions._packs_cache["market-relevance-v1"] = pack.model_copy(
            update={"version": "88.0.0"}
        )
        await service.qualify(
            analysis,
            understanding,
            "context",
            institution_context={"name": "Escola de Negócios e Seguros"},
        )
        assert "competências" in job.sanitized_data["_qualification"]["reason"]
        assert job.sanitized_data["_qualification"]["use_for"] == ["sector_context"]
    await engine.dispose()
