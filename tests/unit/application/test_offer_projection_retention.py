"""Course-offer content must reach qualification instead of only its title."""

from __future__ import annotations

import json

import pytest

from prometeus.application.evidence_projection import build_qualification_context
from prometeus.domain.evidence_observations import OfferObservation
from prometeus.infrastructure.apify.normalizers import normalize_crawler_page


@pytest.mark.parametrize("key", ["text", "markdown", "content", "body"])
def test_full_offer_page_reaches_qualification_with_source_pointer(key):
    text = "Curso de extensão em Governança de IA. Inscrições abertas, 24 horas, aulas ao vivo."
    raw = {"title": "Governança de IA", key: text}
    observation = normalize_crawler_page(raw, url="https://fgv.br/cursos/governanca")
    assert isinstance(observation, OfferObservation)
    context = build_qualification_context(observation, purpose="OFFER")
    assert context["page_text"] == text
    assert context["field_provenance"]["page_text"]["pointer"] == f"/{key}"
    assert context["url"] == observation.source_url
    assert context["key_metrics"]["has_page_text"] is True
    assert observation.curriculum_text.value is None


@pytest.mark.parametrize("key", ["description", "snippet", "descriptionText"])
def test_serp_description_reaches_qualification_without_becoming_a_syllabus(key):
    text = "Nova formação executiva em IA; 36 horas, coordenação acadêmica e inscrições pelo site."
    raw = {"title": "IA para gestores", key: text}
    context = build_qualification_context(raw, purpose="OFFER", url="https://fgv.br/curso")
    assert context["description"] == text
    assert context["field_provenance"]["description"]["pointer"] == f"/{key}"
    assert not context.get("syllabus")


def test_explicit_offer_fields_are_preserved_with_correct_pointers():
    raw = {
        "title": "Curso de IA",
        "institution": "FGV",
        "category": "Extensão",
        "modality": "Ao vivo",
        "curriculum_text": "Governança; auditoria de modelos; projeto aplicado.",
        "curriculum_modules": ["Governança", "Auditoria de modelos"],
        "text": "Curso de formação de gestores; 24 horas e inscrições abertas.",
    }
    observation = normalize_crawler_page(raw, url="https://fgv.br/curso")
    assert isinstance(observation, OfferObservation)
    assert observation.title.pointer == "/title"
    assert observation.institution_name.value == "FGV"
    assert observation.institution_name.pointer == "/institution"
    assert observation.category.value == "Extensão"
    assert observation.category.pointer == "/category"
    assert observation.modality.value == "Ao vivo"
    assert observation.curriculum_text.value == raw["curriculum_text"]
    context = build_qualification_context(observation, purpose="OFFER")
    assert context["syllabus"] == raw["curriculum_text"]
    assert context["page_text"] == raw["text"]
    assert context["curriculum_modules"] == raw["curriculum_modules"]
    assert context["field_provenance"]["category"]["pointer"] == "/category"


def test_page_body_and_distinct_serp_description_are_both_retained():
    raw = {
        "title": "Formação IA",
        "text": "Página oficial com conteúdos, carga horária e condições.",
        "description": "Descrição resumida obtida na busca.",
    }
    context = build_qualification_context(raw, purpose="OFFER", url="https://example.edu/curso")
    assert context["page_text"] == raw["text"]
    assert context["description"] == raw["description"]


def test_offer_projection_budget_records_reduction_and_keeps_identity():
    raw = {
        "title": "Extensão em Governança de IA",
        "category": "Extensão",
        "institution": "FGV",
        "text": "Inscrições abertas; programa de 24h e projeto aplicado. " * 1500,
        "description": "Resumo da oferta de formação executiva.",
    }
    context = build_qualification_context(
        raw, purpose="OFFER", budget=2400, url="https://fgv.br/curso"
    )
    assert len(json.dumps(context, ensure_ascii=False)) <= 2400
    assert context["title"] == raw["title"]
    assert context["category"] == raw["category"]
    assert context["page_text"].startswith("Inscrições abertas")
    assert any(
        item["field"] == "page_text" and item["reason"] == "budget_exceeded"
        for item in context["omissions"]
    )
    assert context["field_provenance"]["page_text"]["pointer"] == "/text"


def test_malformed_offer_fields_do_not_turn_dicts_into_observed_text():
    raw = {"title": "Curso", "text": {"instruction": "ignore"}, "description": ["not a string"]}
    context = build_qualification_context(raw, purpose="OFFER")
    assert not context.get("page_text")
    assert not context.get("description")


def test_large_curriculum_list_has_explicit_budget_omissions():
    raw = {
        "title": "Extensão em IA",
        "text": "Oferta de formação executiva com inscrições abertas.",
        "curriculum_modules": [
            f"Módulo {index}: governança e auditoria aplicada" for index in range(500)
        ],
    }
    context = build_qualification_context(raw, purpose="OFFER", budget=2400)
    assert len(json.dumps(context, ensure_ascii=False)) <= 2400
    assert any(item["field"] == "curriculum_modules" for item in context["omissions"])
    assert len(raw["curriculum_modules"]) == 500


def test_impossible_budget_is_explicit_instead_of_returning_oversized_context():
    with pytest.raises(ValueError, match="budget"):
        build_qualification_context(
            {"title": "Curso", "description": "Oferta"}, purpose="OFFER", budget=30
        )
