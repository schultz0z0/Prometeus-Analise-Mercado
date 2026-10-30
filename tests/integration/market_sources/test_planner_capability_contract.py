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


class CapturingLLM(FakeGenerativeModel):
    async def generate_text(self, prompt, system_prompt=None, temperature=0.2):
        self.prompt = prompt
        self.system_prompt = system_prompt
        return self.canned_text


def settings(**changes):
    return AppSettings(
        _env_file=None,
        APIFY_REQUIRED_SOURCES="google_search",
        **{"APIFY_ACTOR_GOOGLE_SEARCH": "apify/google-search-scraper@0.0.474", **changes},
    )


def planner(llm, config=None):
    return CourseResearchPlanner(llm, SkillRegistry("skills"), config or settings())


def payload(capability="google_search", parameters=None):
    return json.dumps(
        {
            "questions": [],
            "tool_calls": [
                {
                    "id": "search",
                    "capability": capability,
                    "query": "curso seguros",
                    "required": True,
                    "rationale": "ofertas e preços",
                    "parameters": parameters or {},
                }
            ],
        }
    )


async def test_catalog_exposes_only_executable_sources_with_semantic_contract():
    llm = CapturingLLM(canned_text=payload())
    await planner(llm).plan(CourseUnderstanding(analysis_id="a", course_title="MBA Seguros"))
    assert '"evidence_expected"' in llm.system_prompt
    assert "concorrentes" in llm.system_prompt.lower()
    assert '"capability": "instagram"' not in llm.system_prompt


async def test_unconfigured_capability_is_rejected_before_execution():
    llm = CapturingLLM(canned_text=payload("instagram"))
    with pytest.raises(ResearchPlanValidationError, match="allowlist|configurada"):
        await planner(llm).plan(CourseUnderstanding(analysis_id="a", course_title="MBA Seguros"))


async def test_planner_discards_llm_supplied_urls_and_assigns_search_dependencies():
    data = json.loads(payload())
    data["tool_calls"].append(
        {
            "id": "crawl",
            "capability": "web_crawler",
            "query": "curso seguros",
            "rationale": "preços",
            "parameters": {"urls": ["http://invented.example/"]},
        }
    )
    llm = CapturingLLM(canned_text=json.dumps(data))
    plan = await planner(
        llm, settings(APIFY_ACTOR_WEB_CRAWLER="apify/website-content-crawler@0.3.102")
    ).plan(CourseUnderstanding(analysis_id="a", course_title="MBA Seguros"))
    crawl = plan.tool_calls[1]
    assert "urls" not in crawl.parameters
    assert crawl.parameters["depends_on"] == ["search"]


async def test_configured_trends_is_planned_even_when_not_a_required_channel():
    llm = CapturingLLM(canned_text=payload())
    plan = await planner(
        llm, settings(APIFY_ACTOR_GOOGLE_TRENDS="apify/google-trends-scraper@0.0.143")
    ).plan(
        CourseUnderstanding(
            analysis_id="a", course_title="MBA Seguros", subject_domains=["seguros"]
        )
    )
    trends = next(call for call in plan.tool_calls if call.capability == "google_trends")
    assert trends.query == "seguros"
    assert trends.parameters["geo"] == "BR"


async def test_followup_removes_dependent_when_its_only_discovery_query_was_already_used():
    data = json.loads(payload())
    data["tool_calls"].append(
        {
            "id": "crawl-new",
            "capability": "web_crawler",
            "query": "nova leitura seguros",
            "rationale": "aprofundar",
            "parameters": {"depends_on": ["search"]},
        }
    )
    llm = CapturingLLM(canned_text=json.dumps(data))
    plan = await planner(
        llm, settings(APIFY_ACTOR_WEB_CRAWLER="apify/website-content-crawler@0.3.102")
    ).plan(
        CourseUnderstanding(analysis_id="a", course_title="Curso Seguros"),
        gaps=["preço comparável"],
        previous_queries=[("google_search", "curso seguros")],
        budget_limit_usd=0.5,
    )
    assert plan.tool_calls == []


async def test_planner_uses_country_and_language_codes_and_does_not_force_tiny_samples():
    data = json.loads(payload())
    data["tool_calls"][0]["max_items"] = 10
    llm = CapturingLLM(canned_text=json.dumps(data))
    result = await planner(llm).plan(
        CourseUnderstanding(
            analysis_id="a",
            course_title="MBA Seguros",
            geography="Brasil como contexto do programa e do mercado estudado; participação online de qualquer localidade.",
            language="Português informado para as disciplinas.",
        )
    )
    call = result.tool_calls[0]
    assert call.parameters["country"] == "BR"
    assert call.parameters["language"] == "pt-BR"
    assert call.parameters["location"] == "Brazil"
    assert call.max_items == 10
    assert "entre 3 e 5" not in llm.prompt
    assert call.parameters["sample_scope"] == "capped_sample"
    assert call.parameters["sufficiency_criterion"]
