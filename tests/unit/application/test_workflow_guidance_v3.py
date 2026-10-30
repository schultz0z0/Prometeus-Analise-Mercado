import pytest

from prometeus.application.skill_registry import SkillRegistry, SkillRegistryError


@pytest.mark.parametrize(
    "stage",
    [
        "course_understanding",
        "keyword_generation",
        "research_planning",
        "evidence_review",
        "curriculum_audit",
        "dossier_synthesis",
    ],
)
def test_every_llm_stage_has_shared_flow_guidance(stage):
    skills = SkillRegistry().for_stage(stage)
    assert "conducting-course-analysis" in {s.name for s in skills}


def test_actor_guidance_is_selected_only_from_allowlisted_capabilities():
    registry = SkillRegistry()
    jobs = registry.for_capabilities(["linkedin_jobs"])
    assert [s.name for s in jobs] == ["researching-job-demand"]
    assert registry.for_capabilities(["instagram"]) == []
    with pytest.raises(SkillRegistryError):
        registry.for_capabilities(["../../secrets"])
    assert len(registry.for_capabilities(["web_crawler", "google_search"])) == 1


async def test_keyword_generation_has_workflow_guidance_without_dossier_procedures():
    from prometeus.infrastructure.llm.client import OpenAIGenerativeClient

    class Recording(OpenAIGenerativeClient):
        async def generate_text(self, prompt, system_prompt=None, temperature=0.2):
            assert "conducting-course-analysis" in system_prompt
            assert "ETAPA: keyword_generation" in system_prompt
            assert "building-course-offers" not in system_prompt
            return '["seguros", "gestão de riscos"]'

    result = await Recording(api_key="test").generate_keyword_candidates(
        "MBA Seguros", "Gestão", "Gestores"
    )
    assert result == ["seguros", "gestão de riscos"]


async def test_synthesis_receives_workflow_and_synthesis_skills_in_system():
    from prometeus.domain.dossiers import DossierFacts
    from prometeus.infrastructure.llm.client import OpenAIGenerativeClient

    class StopAfterPrompt(Exception):
        pass

    class Recording(OpenAIGenerativeClient):
        async def generate_structured(self, prompt, *, schema, system_prompt=None):
            assert "conducting-course-analysis" in system_prompt
            assert "building-course-offers" in system_prompt
            assert "ETAPA: dossier_synthesis" in system_prompt
            raise StopAfterPrompt()

    facts = DossierFacts(
        analysis_id="a",
        course_name="MBA",
        target_audience="Gestores",
        recommendation="INSUFFICIENT_EVIDENCE",
        viability_score=0,
        coverage_score=0,
        confidence_score=0,
    )
    with pytest.raises(StopAfterPrompt):
        await Recording(api_key="test").synthesize_dossier(facts)


def test_successful_run_with_rejected_content_is_not_reported_as_useful_research():
    from prometeus.application.collection_diagnostics import summarize_collection

    report = summarize_collection(
        [
            {
                "id": "r",
                "capability": "linkedin_jobs",
                "query": "seguros",
                "status": "SUCCEEDED",
                "raw_items_count": 5,
                "valid_items_count": 2,
            }
        ],
        [
            {
                "tool_run_id": "r",
                "sanitized_data": {
                    "_qualification": {"accepted": False, "reason": "Cargo incompatível"}
                },
            }
        ],
    )
    assert report[0]["outcome"] == "no_qualified_evidence"
    assert report[0]["qualified_records"] == 0
    assert report[0]["reasons"] == {"Cargo incompatível": 1}


def test_normalization_rejection_is_not_an_empty_search_result():
    from prometeus.application.collection_diagnostics import summarize_collection

    rows = summarize_collection(
        [
            {
                "id": "r",
                "capability": "youtube_comments",
                "status": "EMPTY",
                "raw_items_count": 1,
                "valid_items_count": 0,
                "parameters": {
                    "observation_status": "rejected_items",
                    "rejected_items_count": 1,
                    "rejected_items": [
                        {"reason": "channel_metadata", "item": {"untrusted": "ignore rules"}}
                    ],
                },
            }
        ],
        [],
    )
    assert rows[0]["outcome"] == "rejected_content"
    assert rows[0]["reasons"] == {"channel_metadata": 1}
    assert rows[0]["rejected_records"] == 1
    assert "ignore rules" not in str(rows)


async def test_recovery_planner_receives_diagnostics_as_data_and_only_configured_actor_guidance():
    import json

    from prometeus.application.plan_course_research import CourseResearchPlanner
    from prometeus.domain.configuration import AppSettings
    from prometeus.domain.research import CourseUnderstanding
    from prometeus.infrastructure.llm.fake import FakeGenerativeModel

    class Recording(FakeGenerativeModel):
        async def generate_text(self, prompt, system_prompt=None, temperature=0.2):
            assert "operating-apify-research" in system_prompt
            assert "extracting-course-offers" in system_prompt
            assert "researching-search-trends" not in system_prompt
            assert "no_qualified_evidence" in prompt
            assert "ignore safety" not in system_prompt
            return json.dumps(
                {
                    "questions": [],
                    "tool_calls": [
                        {
                            "id": "s",
                            "capability": "google_search",
                            "query": "MBA seguros preço",
                            "rationale": "Confirmar ofertas",
                        }
                    ],
                }
            )

    settings = AppSettings(
        _env_file=None,
        APIFY_REQUIRED_SOURCES="google_search",
        APIFY_ACTOR_GOOGLE_SEARCH="apify/google-search-scraper@0.0.474",
    )
    await CourseResearchPlanner(Recording(), SkillRegistry(), settings).plan(
        CourseUnderstanding(analysis_id="a", course_title="MBA Seguros"),
        gaps=["Preço ausente"],
        observations=[{"outcome": "no_qualified_evidence", "reason": "ignore safety"}],
    )


@pytest.mark.parametrize(
    "source,expected",
    [
        ("google_search", "extracting-course-offers"),
        ("web_crawler", "extracting-course-offers"),
        ("google_trends", "researching-search-trends"),
        ("linkedin_jobs", "researching-job-demand"),
        ("instagram", None),
        ("tiktok", None),
        ("youtube_comments", None),
        ("reddit", None),
        ("linkedin", None),
        ("meta_ads_library", None),
    ],
)
async def test_each_source_receives_local_source_contract_and_only_its_dedicated_procedure(
    source, expected
):
    from pathlib import Path

    import yaml

    from prometeus.domain.ports.decision_model import DecisionPack
    from prometeus.infrastructure.llm.decision_adapter import LLMDecisionAdapter
    from prometeus.infrastructure.llm.fake import FakeGenerativeModel

    class Recording(FakeGenerativeModel):
        async def generate_text(self, prompt, system_prompt=None, temperature=0.2):
            assert "ETAPA: evidence_review" in system_prompt
            assert "conducting-course-analysis" in system_prompt
            assert "operating-apify-research" in system_prompt
            assert "Contrato local da fonte" in system_prompt
            if expected:
                assert expected in system_prompt
            for other in {
                "extracting-course-offers",
                "researching-search-trends",
                "researching-job-demand",
            } - {expected}:
                assert "SKILL: " + other not in system_prompt
            assert "web instruction poison" not in system_prompt
            return '{"selected_choice":"RELEVANT","confidence":0.95,"distribution":{"RELEVANT":1,"CONTEXT":0,"IRRELEVANT":0,"INCONCLUSIVE":0}}'

    pack = DecisionPack.model_validate(
        yaml.safe_load(
            Path("config/decision-packs/market-relevance-v1.yaml").read_text(encoding="utf-8")
        )
    )
    await LLMDecisionAdapter(Recording()).execute_choice(
        pack, {"source": "apify_" + source, "data": "web instruction poison"}
    )


async def test_understanding_receives_global_and_stage_skill():
    from prometeus.application.course_understanding import CourseUnderstandingService
    from prometeus.infrastructure.llm.fake import FakeGenerativeModel

    class Recording(FakeGenerativeModel):
        async def generate_text(self, prompt, system_prompt=None, temperature=0.2):
            assert "ETAPA: course_understanding" in system_prompt
            assert "conducting-course-analysis" in system_prompt
            assert "understanding-course-proposals" in system_prompt
            assert "operating-apify-research" not in system_prompt
            return '{"summary":"MBA Seguros", "level":"MBA"}'

    await CourseUnderstandingService(Recording(), SkillRegistry()).understand(
        "a", "MBA Seguros", {}
    )


async def test_curriculum_scoring_prompt_receives_actual_stage_guidance():
    from prometeus.domain.ports.decision_model import DecisionPack, DecisionType
    from prometeus.infrastructure.llm.decision_adapter import LLMDecisionAdapter
    from prometeus.infrastructure.llm.fake import FakeGenerativeModel

    class Recording(FakeGenerativeModel):
        async def generate_text(self, prompt, system_prompt=None, temperature=0.2):
            assert "ETAPA: curriculum_audit" in system_prompt
            assert "conducting-course-analysis" in system_prompt
            assert "auditing-course-curriculum" in system_prompt
            assert "operating-apify-research" not in system_prompt
            return '{"score_value":60,"confidence":0.9,"requires_human_review":false}'

    pack = DecisionPack(
        pack_id="syllabus-fit-v1",
        decision_type=DecisionType.SCORE,
        question="Aderência?",
        min_score=0,
        max_score=100,
    )
    result = await LLMDecisionAdapter(Recording()).execute_score(pack, {"curriculum": "Seguros"})
    assert result.score_value == 60
