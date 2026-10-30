from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.domain.analyses import Analysis
from prometeus.domain.research import CourseUnderstanding
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base, HistoricalCourseModel, HistoricalFunnelModel


@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        yield session
    await engine.dispose()


async def seed(
    db,
    name,
    n,
    *,
    category="MBA Executivo",
    tenant="ens",
    curriculum="Gestão de riscos e subscrição",
    complete=True,
):
    course = HistoricalCourseModel(
        id=name,
        external_id=name,
        tenant_id=tenant,
        name=f"MBA {name} Gestão de Riscos e Seguros",
        category=category,
        modality="online",
        workload_hours=360,
        tags=["riscos", "seguros"],
        target_audience=["gestores"],
        curriculum_text=curriculum,
    )
    db.add(course)
    db.add(
        HistoricalFunnelModel(
            id=f"f-{name}",
            course_id=name,
            external_course_id=name,
            period="2025",
            leads=n * 10,
            applicants=n * 5,
            enrolled=n,
            average_ticket_brl=10000 + n,
            total_revenue_brl=(10000 + n) * n,
            price_period="total",
            data_complete=complete,
            cohort_status="COMPLETED",
        )
    )
    await db.commit()


async def context(db):
    analysis = Analysis.create(
        tenant_id="ens", course_name="MBA Gestão de Riscos de Seguros", correlation_id="ipd"
    )
    analysis.proposal_data = {"curriculum": "Gestão de riscos e subscrição"}
    await AnalysisRepository(db).save(analysis)
    await db.commit()
    return analysis, CourseUnderstanding(
        analysis_id=analysis.id,
        course_title=analysis.course_name,
        level="MBA Executivo",
        subject_domains=["seguros", "riscos"],
        target_audiences=["gestores"],
    )


async def test_ipd_is_percentile_within_family_and_selects_at_most_three_comparables(db):
    from prometeus.application.internal_history import InternalHistoryService

    for name, n in [("baixo", 10), ("medio", 20), ("alto", 30), ("mais-alto", 40)]:
        await seed(db, name, n)
    await seed(db, "extensao", 999, category="Extensão")
    await seed(db, "foreign", 999, tenant="other")
    analysis, understanding = await context(db)
    features, audit = await InternalHistoryService(db, None).build(analysis, understanding, "ipd")
    assert audit["reference_n"] == 4
    assert len(audit["comparables"]) == 3
    assert {item["family"] for item in audit["comparables"]} == {"pos_mba"}
    assert not {"extensao", "foreign"} & {item["course_id"] for item in audit["comparables"]}
    assert features.require("internal_ipd_score").value == pytest.approx(
        sum(c["ipd_score"] for c in audit["comparables"]) / 3, abs=0.01
    )
    assert all(c["curriculum_fit"] is not None for c in audit["comparables"])
    assert {c["source"] for c in audit["observed_prices"]} == {"internal"}


async def test_small_cohort_does_not_fabricate_score_and_missing_grade_is_explained(db):
    from prometeus.application.internal_history import InternalHistoryService

    await seed(db, "one", 20, curriculum="")
    analysis, understanding = await context(db)
    features, audit = await InternalHistoryService(db, None).build(analysis, understanding, "ipd")
    assert features.get("internal_ipd_score") is None
    assert audit["reference_n"] == 1
    assert audit["comparables"][0]["curriculum_fit"] is None
    assert any("grade" in reason.lower() for reason in audit["limitations"])
    assert any("três" in reason.lower() for reason in audit["limitations"])


async def test_no_unrelated_course_is_added_just_to_fill_three_slots(db):
    from prometeus.application.internal_history import InternalHistoryService

    for name, n in [("match", 20), ("other-a", 30), ("other-b", 40)]:
        await seed(db, name, n)
    from sqlalchemy import select

    courses = list((await db.execute(select(HistoricalCourseModel))).scalars())
    for course in courses:
        if course.id != "match":
            course.name = "MBA em Gastronomia e Cozinha"
            course.tags = ["gastronomia", "cozinha"]
            course.curriculum_text = "Técnicas de cozinha e panificação"
    await db.commit()
    analysis, understanding = await context(db)
    _features, audit = await InternalHistoryService(db, None).build(analysis, understanding, "ipd")
    assert audit["reference_n"] == 3
    assert [course["course_id"] for course in audit["comparables"]] == ["match"]


async def test_unknown_price_unit_is_not_silently_assumed_total(db):
    from prometeus.application.internal_history import InternalHistoryService

    for name, n in [("low", 10), ("mid", 20), ("high", 30)]:
        await seed(db, name, n)
    record = await db.get(HistoricalFunnelModel, "f-low")
    record.price_period = "monthly"
    await db.commit()
    analysis, understanding = await context(db)
    _features, audit = await InternalHistoryService(db, None).build(analysis, understanding, "ipd")
    assert {item["course_id"] for item in audit["observed_prices"]} == {"mid", "high"}


async def test_missing_metric_is_not_seeded_as_an_observed_zero(db, monkeypatch):
    from prometeus.infrastructure.institutional.ens import seeder

    monkeypatch.setattr(
        seeder,
        "ENS_HISTORICAL_PORTFOLIO",
        [
            {
                "external_id": "missing",
                "name": "MBA Seguros",
                "category": "MBA Executivo",
                "modality": "online",
                "workload_hours": 360,
                "status": "active",
                "tags": ["seguros"],
                "target_audience": [],
                "funnel_history": [
                    {
                        "period": "2025",
                        "leads": 100,
                        "applicants": None,
                        "enrolled": 10,
                        "status": "COMPLETED",
                        "average_ticket_brl": 10000,
                    }
                ],
            }
        ],
    )
    await seeder.seed_historical_courses(db)
    from sqlalchemy import select

    record = (await db.execute(select(HistoricalFunnelModel))).scalar_one()
    assert record.data_complete is False


async def test_ties_zero_and_incomplete_data_are_distinct(db):
    from prometeus.application.internal_history import InternalHistoryService

    for name, n in [("zero", 0), ("same-a", 10), ("same-b", 10)]:
        await seed(db, name, n)
    await seed(db, "incomplete", 100, complete=False)
    analysis, understanding = await context(db)
    features, audit = await InternalHistoryService(db, None).build(analysis, understanding, "ipd")
    assert audit["reference_n"] == 3
    rows = {c["course_id"]: c for c in audit["comparables"]}
    assert rows["zero"]["ipd_score"] == 0
    assert rows["same-a"]["ipd_score"] == rows["same-b"]["ipd_score"] == 75
    assert features.require("internal_ipd_confidence").value <= 0.9


def test_family_normalization_does_not_mix_degree_with_postgraduate():
    from prometeus.application.internal_history import normalize_family, percentile_rank

    assert (
        normalize_family("Pós-Graduação Lato Sensu")
        == normalize_family("MBA Executivo")
        == "pos_mba"
    )
    assert normalize_family("Graduação Tecnológica") == "graduacao"
    assert percentile_rank(10, [0, 10, 10]) == 75
