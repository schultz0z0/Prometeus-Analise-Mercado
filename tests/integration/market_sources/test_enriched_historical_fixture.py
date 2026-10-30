from collections import Counter
from urllib.parse import urlsplit

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.internal_history import InternalHistoryService
from prometeus.application.pricing_reference import build_price_reference
from prometeus.domain.analyses import Analysis
from prometeus.domain.research import CourseUnderstanding
from prometeus.infrastructure.db.models import Base, HistoricalCourseModel, HistoricalFunnelModel
from prometeus.infrastructure.institutional.ens.dataset import ENS_HISTORICAL_PORTFOLIO
from prometeus.infrastructure.institutional.ens.seeder import seed_historical_courses


def test_fixture_supports_family_percentiles_with_explicit_synthetic_metadata():
    assert len(ENS_HISTORICAL_PORTFOLIO) == 33
    assert Counter(c["family"] for c in ENS_HISTORICAL_PORTFOLIO) == {
        "pos_mba": 10,
        "extensao": 10,
        "qualificacao_tecnica": 10,
        "graduacao": 1,
        "imersao": 1,
        "certificacao_avancada": 1,
    }
    for course in ENS_HISTORICAL_PORTFOLIO:
        assert course["is_synthetic"] is True
        assert course["dataset_version"]
        assert len(course["curriculum_modules"]) >= 4
        assert course["curriculum_text"]
        assert {f["period"] for f in course["funnel_history"]} == {"2024", "2025"}
        for f in course["funnel_history"]:
            assert 0 <= f["enrolled"] <= f["applicants"] <= f["leads"]
            assert f["data_complete"] is True and f["price_period"] == "total"
            assert f["status"] in {"COMPLETED", "CANCELLED_LOW_QUORUM"}
            assert f["average_ticket_brl"] > 0
            expected = (
                0
                if f["status"] == "CANCELLED_LOW_QUORUM"
                else f["enrolled"] * f["average_ticket_brl"]
            )
            assert f["total_revenue_brl"] == pytest.approx(expected)
    latest = [c["funnel_history"][-1] for c in ENS_HISTORICAL_PORTFOLIO]
    assert any(f["enrolled"] == 0 for f in latest)
    assert any(f["enrolled"] >= 80 for f in latest)


def test_official_academic_references_never_relabel_simulated_funnels_as_real():
    referenced = [c for c in ENS_HISTORICAL_PORTFOLIO if c.get("academic_reference")]
    assert len(referenced) == 12
    for c in referenced:
        reference = c["academic_reference"]
        assert urlsplit(reference["source_url"]).hostname.endswith("ens.edu.br")
        assert reference["checked_at"] == "2026-10-28"
        assert set(reference["verified_fields"]) <= {
            "name",
            "category",
            "workload_hours",
            "modality",
        }
        assert c["curriculum_origin"] == "synthetic"
        assert c["funnel_origin"] == "synthetic"
        assert c["price_origin"] == "synthetic"
        assert c["is_synthetic"] is True


def test_official_categories_remain_distinct_from_the_shared_ipd_family():
    courses = {c["external_id"]: c for c in ENS_HISTORICAL_PORTFOLIO}
    for external_id, category, family in [
        ("ENS-MBA-SEG-01", "MBA", "pos_mba"),
        ("ENS-POS-COMP-12", "Pós-Graduação", "pos_mba"),
        ("ENS-EXT-RES-14", "Extensão", "extensao"),
        ("ENS-TEST-GRAD-31", "Graduação Tecnológica", "graduacao"),
        ("ENS-TEST-IMERSAO-32", "Imersão Internacional", "imersao"),
        ("ENS-TEST-CERT-33", "Certificação Avançada", "certificacao_avancada"),
    ]:
        assert courses[external_id]["category"] == category
        assert courses[external_id]["family"] == family


async def test_seed_is_idempotent_and_enables_actual_ipd_and_internal_price_without_analysis_writes():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            await seed_historical_courses(db, reset=False)
            ids_before = set((await db.execute(select(HistoricalCourseModel.id))).scalars())
            stats = await seed_historical_courses(db, reset=False)
            assert stats["courses_created"] == 0 and stats["courses_updated"] == 33
            assert set((await db.execute(select(HistoricalCourseModel.id))).scalars()) == ids_before
            assert await db.scalar(select(func.count()).select_from(HistoricalFunnelModel)) == 66
            proposal = Analysis.create(
                tenant_id="ens",
                course_name="MBA Gestão Avançada de Seguros",
                correlation_id="fixture",
            )
            proposal.proposal_data = {
                "curriculum": "Gestão de seguros e resseguros, estratégia, liderança, subscrição, sinistros, finanças e gestão de riscos"
            }
            understanding = CourseUnderstanding(
                analysis_id=proposal.id,
                course_title=proposal.course_name,
                level="MBA Executivo",
                subject_domains=["seguros", "resseguros", "gestão de riscos"],
                target_audiences=["gestores de seguradoras"],
            )
            features, audit = await InternalHistoryService(db).build(proposal, understanding)
            assert audit["reference_n"] == 10
            assert len(audit["comparables"]) == 3
            assert features.require("internal_ipd_confidence").value == 0.9
            assert all(c["curriculum_fit"] is not None for c in audit["comparables"])
            assert len({c["ipd_score"] for c in audit["comparables"]}) > 1
            price = build_price_reference(
                course_title=proposal.course_name,
                level=understanding.level,
                institution_name="ENS",
                internal_prices=audit["observed_prices"],
                offers=[],
            )
            assert price["internal_count"] > 0
            assert price["mean_total_brl"] > 0
            # This check computes in memory and never creates/changes an analysis.
            from prometeus.infrastructure.db.models import AnalysisModel

            assert await db.scalar(select(func.count()).select_from(AnalysisModel)) == 0
    finally:
        await engine.dispose()
