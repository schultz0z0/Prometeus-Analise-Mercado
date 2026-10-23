import json

import pytest

from prometeus.application.course_understanding import CourseUnderstandingService
from prometeus.application.skill_registry import SkillRegistry
from prometeus.infrastructure.llm.fake import FakeGenerativeModel


@pytest.mark.asyncio
async def test_llm_understands_proposal_and_attached_curriculum_before_research() -> None:
    llm = FakeGenerativeModel(
        canned_text=json.dumps(
            {
                "summary": "Formação executiva sobre aplicação de IA em subscrição.",
                "subject_domains": ["seguros", "inteligência artificial"],
                "target_audiences": ["subscritores", "gestores de risco"],
                "learning_outcomes": ["aplicar IA na avaliação de riscos"],
                "level": "pós-graduação",
                "modality": "online síncrono",
                "geography": "Brasil",
                "language": "pt-BR",
                "proposed_price_brl": 12900,
                "duration_months": 12,
                "supplied_materials": ["ementa.pdf"],
                "uncertainties": ["carga horária não informada"],
                "hypotheses": ["profissionais de resseguros podem ser público secundário"],
            },
            ensure_ascii=False,
        )
    )
    service = CourseUnderstandingService(llm, SkillRegistry("skills"))

    result = await service.understand(
        analysis_id="anl-123",
        course_title="MBA em IA Aplicada à Subscrição",
        proposal={
            "target_audience": "Subscritores e gestores de risco",
            "curriculum_text": "Módulo 1: fundamentos. Módulo 2: laboratório de subscrição.",
            "curriculum_file_name": "ementa.pdf",
            "ticket": 12900,
        },
    )

    assert result.analysis_id == "anl-123"
    assert result.course_title == "MBA em IA Aplicada à Subscrição"
    assert result.subject_domains == ["seguros", "inteligência artificial"]
    assert result.supplied_materials == ["ementa.pdf"]
    assert result.uncertainties == ["carga horária não informada"]


@pytest.mark.asyncio
async def test_course_understanding_rejects_non_json_instead_of_guessing() -> None:
    service = CourseUnderstandingService(
        FakeGenerativeModel(canned_text="Parece um curso promissor."),
        SkillRegistry("skills"),
    )

    with pytest.raises(ValueError, match="JSON"):
        await service.understand("anl-1", "Curso", {"description": "Breve"})

