import json

from prometeus.application.course_understanding import CourseUnderstandingService
from prometeus.application.skill_registry import SkillRegistry
from prometeus.infrastructure.llm.fake import FakeGenerativeModel


async def test_installments_use_total_price_in_code_and_keep_academic_duration_separate():
    llm = FakeGenerativeModel(
        canned_text=json.dumps(
            {"summary": "Curso", "proposed_price_brl": 13664, "duration_months": 20}
        )
    )
    result = await CourseUnderstandingService(llm, SkillRegistry()).understand(
        "test",
        "MBA",
        {"ticket": 976, "price_period": "monthly", "installments_count": 20, "duration_months": 14},
    )
    assert result.proposed_price_brl == 19520
    assert result.proposed_price_period == "total"
    assert result.duration_months == 14


async def test_document_content_is_not_silently_truncated_before_understanding():
    class RecordingLLM(FakeGenerativeModel):
        async def generate_text(self, prompt, system_prompt=None, temperature=0.2):
            assert "FINAL DA EMENTA" in prompt
            return "{}"

    await CourseUnderstandingService(RecordingLLM(), SkillRegistry()).understand(
        "test", "MBA", {"curriculum": "Conteúdo " * 10000 + "FINAL DA EMENTA"}
    )


async def test_declared_total_is_not_multiplied_again_by_financing_installments():
    result = await CourseUnderstandingService(
        FakeGenerativeModel(canned_text="{}"), SkillRegistry()
    ).understand(
        "test",
        "MBA",
        {"ticket": 12000, "price_period": "total", "installments_count": 12, "duration_months": 10},
    )
    assert result.proposed_price_brl == 12000
    assert result.proposed_price_period == "total"


async def test_declared_institution_and_locale_are_structured_not_inferred_from_document():
    result = await CourseUnderstandingService(
        FakeGenerativeModel(
            canned_text='{"geography":"Brasil como contexto do programa; online", "language":"Português no documento"}'
        ),
        SkillRegistry(),
    ).understand(
        "test",
        "MBA",
        {
            "_institution_context": {"name": "ENS", "domains": ["ens.edu.br"]},
            "geography": "Brasil",
            "language": "pt-BR",
        },
    )
    assert result.institution_name == "ENS"
    assert result.institution_domains == ["ens.edu.br"]
    assert result.geography == "Brasil"
    assert result.language == "pt-BR"
