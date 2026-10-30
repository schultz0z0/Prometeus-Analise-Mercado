import json

import pytest

from prometeus.application.plan_course_research import (
    CourseResearchPlanner,
    ResearchPlanValidationError,
)
from prometeus.application.skill_registry import SkillRegistry
from prometeus.domain.configuration import AppSettings
from prometeus.domain.research import CourseUnderstanding
from prometeus.infrastructure.llm.fake import FakeGenerativeModel


def make_settings() -> AppSettings:
    return AppSettings(
        _env_file=None,
        APIFY_REQUIRED_SOURCES="google_search,meta_ads_library,linkedin_jobs",
        APIFY_ACTOR_GOOGLE_SEARCH="apify/google-search-scraper@0.0.474",
        APIFY_ACTOR_META_AD_LIBRARY="igolaizola/facebook-ad-library-scraper@0.0.59",
        APIFY_ACTOR_LINKEDIN_JOBS="curious_coder/linkedin-jobs-scraper@1.7.18",
        APIFY_MAX_TOTAL_CHARGE_USD_PER_ANALYSIS=4.5,
    )


@pytest.mark.asyncio
async def test_research_plan_is_course_specific_and_covers_required_sources() -> None:
    llm = FakeGenerativeModel(
        canned_text=json.dumps(
            {
                "questions": [
                    {
                        "id": "q-demand",
                        "question": "Quais ofertas competem por subscritores?",
                        "evidence_need": "ofertas e diferenciais",
                        "priority": 1,
                    }
                ],
                "tool_calls": [
                    {
                        "id": "google-offers",
                        "capability": "google_search",
                        "query": "MBA IA subscrição de riscos seguros Brasil",
                        "required": True,
                        "rationale": "Mapear ofertas concorrentes",
                        "max_items": 30,
                        "parameters": {"country": "BR", "language": "pt"},
                        "question_ids": ["q-demand"],
                    },
                    {
                        "id": "meta-ads",
                        "capability": "meta_ads_library",
                        "query": "IA subscrição seguros curso",
                        "required": True,
                        "rationale": "Observar anunciantes e criativos ativos",
                        "max_items": 50,
                        "parameters": {"country": "BR"},
                        "question_ids": ["q-demand"],
                    },
                    {
                        "id": "linkedin-jobs",
                        "capability": "linkedin_jobs",
                        "query": "subscritor inteligência artificial seguros",
                        "required": True,
                        "rationale": "Medir competências demandadas",
                        "max_items": 50,
                        "parameters": {"location": "Brasil"},
                        "question_ids": ["q-demand"],
                    },
                ],
            },
            ensure_ascii=False,
        )
    )
    understanding = CourseUnderstanding(
        analysis_id="anl-123",
        course_title="MBA em IA Aplicada à Subscrição",
        subject_domains=["seguros", "inteligência artificial"],
        target_audiences=["subscritores"],
    )
    planner = CourseResearchPlanner(llm, SkillRegistry("skills"), make_settings())

    plan = await planner.plan(understanding)

    assert plan.analysis_id == "anl-123"
    assert plan.budget_limit_usd == 4.5
    assert {call.capability for call in plan.tool_calls} == {
        "google_search",
        "meta_ads_library",
        "linkedin_jobs",
    }
    assert all(
        "subscr" in call.query.lower() or "ia" in call.query.lower() for call in plan.tool_calls
    )
    assert plan.skill_snapshots[0]["name"] == "planning-market-research"


@pytest.mark.asyncio
async def test_research_plan_rejects_missing_required_source() -> None:
    llm = FakeGenerativeModel(
        canned_text=json.dumps(
            {
                "questions": [],
                "tool_calls": [
                    {
                        "id": "only-google",
                        "capability": "google_search",
                        "query": "curso seguros",
                        "required": True,
                        "rationale": "pesquisar",
                    }
                ],
            }
        )
    )
    planner = CourseResearchPlanner(llm, SkillRegistry("skills"), make_settings())

    with pytest.raises(ResearchPlanValidationError, match="fontes obrigatórias"):
        await planner.plan(
            CourseUnderstanding(analysis_id="anl-1", course_title="Curso de Seguros")
        )
