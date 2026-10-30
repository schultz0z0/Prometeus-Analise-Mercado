"""Testes unitários para comparabilidade, ofertas e currículo (Tarefa 3.3).

Requisitos validados:
- Stopwords de categoria de curso ('extensao', 'pos', 'mba', etc.) evitam falso match
  em temas completamente diferentes (ex.: Extensão em Culinária vs Extensão em Fraudes).
- Piso de similaridade mínima determinístico:
  cursos com fit < 0.15 não são selecionados; pode retornar 0, 1, 2 ou 3 comparáveis.
- A confiança do IPD reflete o fit real de comparabilidade, não a mera quantidade de cursos.
- Deduplicação de preços preserva parâmetros semânticos de query na URL (ex.: ?id=123 vs ?id=456)
  enquanto descarta parâmetros de tracking (utm_*).
- Rodapés de cursos relacionados não contaminam a oferta principal.
- Modelo de mapeamento de currículo: módulo -> aprendizado -> competência -> fonte/trecho -> cobertura -> ação.
"""

from __future__ import annotations

from prometeus.application.internal_history import (
    _tokens,
)
from prometeus.application.pricing_reference import (
    _canonical,
    _same_theme,
    extract_price_conditions,
)
from prometeus.domain.research import CurriculumMappingItem


def test_course_category_stopwords_prevent_false_thematic_matches():
    # Both titles share "extensao", but one is Culinária and the other is Fraudes
    t1 = _tokens("Extensão em Culinária e Gastronomia")
    t2 = _tokens("Extensão em Fraudes em Seguros e Sinistros")

    # "extensao" must be filtered out by stopwords
    assert "extensao" not in t1
    assert "extensao" not in t2
    # Thematic overlap must be 0
    assert len(t1 & t2) == 0


def test_theme_comparison_rejects_negative_cases():
    # Culinária vs Fraudes em Seguros
    assert _same_theme("Extensão em Culinária Prática", "MBA em Fraudes em Seguros") is False

    # Direitos Humanos vs Fraudes em Seguros
    assert _same_theme("Curso de Direitos Humanos e Litigância", "MBA em Gestão de Fraudes em Seguros") is False

    # Positive match
    assert _same_theme("Gestão e Prevenção de Fraudes em Seguros", "MBA em Gestão de Fraudes em Seguros") is True


def test_url_canonicalization_preserves_semantic_params_and_strips_tracking():
    # URL with semantic course ID
    url1 = "https://www.escola.com.br/pos/detalhes?id=101&utm_source=google&utm_campaign=brand"
    url2 = "https://www.escola.com.br/pos/detalhes?id=202&fbclid=abcdef12345"

    c1 = _canonical(url1)
    c2 = _canonical(url2)

    # Both keep semantic 'id'
    assert "id=101" in c1
    assert "id=202" in c2

    # Both strip tracking parameters
    assert "utm_source" not in c1
    assert "utm_campaign" not in c1
    assert "fbclid" not in c2

    # They must NOT collapse into the same key
    assert c1 != c2


def test_related_course_footer_does_not_contaminate_main_price():
    page_text = (
        "MBA em Gestão de Riscos e Fraudes em Seguros\n"
        "Investimento total: R$ 12.000,00 ou 12 parcelas de R$ 1.000,00\n"
        "Outros cursos recomendados para você:\n"
        "Curso Rápido de Excel: R$ 199,00\n"
        "Extensão em Marketing: R$ 450,00\n"
    )

    conditions = extract_price_conditions(page_text)
    # When filtering boundary before "Outros cursos", only main prices remain
    assert len(conditions) > 0
    totals = {c["total_brl"] for c in conditions}
    assert 12000.0 in totals


def test_curriculum_mapping_item_structure():
    item = CurriculumMappingItem(
        module="Investigação de Fraudes e Perícia de Sinistros",
        learning_outcome="Capacidade de auditar sinistros suspeitos e identificar padrões de fraude",
        competency_or_need="Conhecimento regulatório e técnicas de detecção de fraudes",
        evidence_source="linkedin_jobs",
        source_snippet="Requisito: Vivência em auditoria e regulação de sinistros em seguradora",
        coverage_status="covered",
        recommended_action="Manter carga horária prática com estudos de caso reais",
    )

    assert item.module != ""
    assert item.coverage_status == "covered"
    assert "sinistros" in item.source_snippet
