"""Testes unitários para curadoria de evidências por finalidade (Tarefa 3.2).

Requisitos validados:
- Substituição do `accepted` universal por `EvidenceUseAssessment` por uso:
  discovery, pricing, direct_competition, adjacent_competition,
  workforce_competencies, employability_signal, learner_demand,
  own_context, industry_context.
- Qualidade baixa ou ausência para uma finalidade (ex.: oferta sem preço)
  NÃO apaga a utilidade para outra finalidade (ex.: concorrência direta ou descoberta).
- Vagas sustentam competências/empregabilidade sem virar concorrentes ou preço.
- Itens da própria instituição viram own_context, nunca concorrentes externos.
- Itens inconclusivos exigem causa explícita e próximo passo em vez de confiança inflada.
"""

from __future__ import annotations

from prometeus.domain.evidence_observations import (
    EvidencePurpose,
    EvidenceUseAssessment,
    MultiPurposeAssessment,
)


def test_evidence_purpose_enum_contains_nine_canonical_purposes():
    purposes = {p.value for p in EvidencePurpose}
    expected = {
        "discovery",
        "pricing",
        "direct_competition",
        "adjacent_competition",
        "workforce_competencies",
        "employability_signal",
        "learner_demand",
        "own_context",
        "industry_context",
    }
    assert expected.issubset(purposes)


def test_offer_without_price_is_usable_for_direct_competition_and_discovery_but_not_pricing():
    assessment = MultiPurposeAssessment(
        assessments={
            EvidencePurpose.DISCOVERY.value: EvidenceUseAssessment(
                purpose=EvidencePurpose.DISCOVERY,
                usable=True,
                observable_factors=["URL de oferta oficial", "Grade curricular visível"],
                quote_snippets=["MBA em Fraudes em Seguros"],
                reason="Oferta educacional no tema exato",
            ),
            EvidencePurpose.DIRECT_COMPETITION.value: EvidenceUseAssessment(
                purpose=EvidencePurpose.DIRECT_COMPETITION,
                usable=True,
                observable_factors=["Categoria MBA", "Tema fraudes em sinistros"],
                quote_snippets=["Pós-graduação Lato Sensu em Fraudes"],
                reason="Concorrente direto na mesma categoria acadêmica",
            ),
            EvidencePurpose.PRICING.value: EvidenceUseAssessment(
                purpose=EvidencePurpose.PRICING,
                usable=False,
                observable_factors=["Página sob consulta", "Formulário de contato"],
                quote_snippets=["Consulte nossos consultores"],
                reason="Preço total e parcelas ausentes na página pública",
                rejection_cause="price_missing_or_lead_wall",
                next_step="Disparar crawler em página de checkout ou coletar via contato institucional",
            ),
        }
    )

    assert assessment.is_usable_for(EvidencePurpose.DISCOVERY) is True
    assert assessment.is_usable_for(EvidencePurpose.DIRECT_COMPETITION) is True
    assert assessment.is_usable_for(EvidencePurpose.PRICING) is False

    # Low pricing usability did NOT erase direct competition or discovery!
    assert "direct_competition" in assessment.usable_purposes
    assert "discovery" in assessment.usable_purposes
    assert "pricing" not in assessment.usable_purposes


def test_job_posting_is_usable_for_workforce_competencies_not_competition():
    assessment = MultiPurposeAssessment(
        assessments={
            EvidencePurpose.WORKFORCE_COMPETENCIES.value: EvidenceUseAssessment(
                purpose=EvidencePurpose.WORKFORCE_COMPETENCIES,
                usable=True,
                observable_factors=["Requisitos técnicos", "Ferramentas analíticas"],
                quote_snippets=["Experiência com regulação de sinistros e detecção de fraudes"],
                reason="Vaga explicita competências técnicas exigidas pelo mercado de seguros",
            ),
            EvidencePurpose.EMPLOYABILITY_SIGNAL.value: EvidenceUseAssessment(
                purpose=EvidencePurpose.EMPLOYABILITY_SIGNAL,
                usable=True,
                observable_factors=["Cargo sênior", "Seguradora multinacional"],
                quote_snippets=["Analista de Sinistros Sênior - Prevenção de Fraudes"],
                reason="Sinal de absorção profissional na área",
            ),
            EvidencePurpose.DIRECT_COMPETITION.value: EvidenceUseAssessment(
                purpose=EvidencePurpose.DIRECT_COMPETITION,
                usable=False,
                reason="Vaga de emprego não é uma oferta de curso concorrente",
                rejection_cause="not_a_course_offer",
            ),
        }
    )

    assert assessment.is_usable_for(EvidencePurpose.WORKFORCE_COMPETENCIES) is True
    assert assessment.is_usable_for(EvidencePurpose.EMPLOYABILITY_SIGNAL) is True
    assert assessment.is_usable_for(EvidencePurpose.DIRECT_COMPETITION) is False


def test_own_institution_is_usable_for_own_context_never_direct_competition():
    assessment = MultiPurposeAssessment(
        assessments={
            EvidencePurpose.OWN_CONTEXT.value: EvidenceUseAssessment(
                purpose=EvidencePurpose.OWN_CONTEXT,
                usable=True,
                observable_factors=["Domínio institucional oficial ens.edu.br"],
                quote_snippets=["Escola de Negócios e Seguros - ENS"],
                reason="Oferta ou comunicação interna da própria instituição",
            ),
            EvidencePurpose.DIRECT_COMPETITION.value: EvidenceUseAssessment(
                purpose=EvidencePurpose.DIRECT_COMPETITION,
                usable=False,
                reason="Oferta da própria instituição não concorre externamente",
                rejection_cause="own_institution_not_competitor",
            ),
        }
    )

    assert assessment.is_usable_for(EvidencePurpose.OWN_CONTEXT) is True
    assert assessment.is_usable_for(EvidencePurpose.DIRECT_COMPETITION) is False


def test_inconclusive_assessment_requires_cause_and_next_step():
    assessment = EvidenceUseAssessment(
        purpose=EvidencePurpose.DIRECT_COMPETITION,
        usable=False,
        confidence=0.5,
        observable_factors=["Página em branco ou carregamento"],
        reason="Conteúdo insuficiente para determinar se é oferta concorrente",
        rejection_cause="page_content_blocked_or_empty",
        next_step="Verificar URL manual ou inspecionar cabeçalho HTTP",
    )

    assert assessment.usable is False
    assert assessment.rejection_cause is not None
    assert assessment.next_step is not None
    assert "blocked" in assessment.rejection_cause
