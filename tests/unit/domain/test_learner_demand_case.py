"""Testes unitários para o modelo de demanda de alunos e contexto ENS (Tarefa 3.4).

Requisitos validados:
- Modelo LearnerDemandCase estruturado:
  - quem compra vs quem faz (buyer_vs_beneficiary: same_individual, employer_b2b, hybrid)
  - tipo de segmento (segment_type: b2c, b2b, b2b2c)
  - público elegível vs público com intenção real de capacitação
  - alternativas consideradas (cursos livres, certificações, treino no trabalho)
  - barreiras e objeções reais (preço, tempo, aplicabilidade)
  - notas de sinais declarados vs comportamentais
  - cenário de conversão/funil plausível para primeira turma
- Regra de inteligência institucional: dados de mercado segurador (SUSEP, CNseg)
  são estritamente contextuais e é PROIBIDO aplicar multiplicadores diretos de matrícula.
"""

from __future__ import annotations

import pytest

from prometeus.domain.research import LearnerDemandCase


def test_learner_demand_case_b2c_individual():
    case = LearnerDemandCase(
        buyer_vs_beneficiary="same_individual",
        segment_type="b2c",
        eligibility_criteria=[
            "Graduação concluída em Direito, Administração, Economia ou Ciências Atuariais",
            "Atuação prévia ou interesse no mercado de seguros ou perícia",
        ],
        training_intent_signals=[
            "Buscas por pós-graduação em regulação de sinistros",
            "Dúvidas sobre perícia securitária e certificação em fóruns e redes sociais",
        ],
        alternatives_considered=[
            "Cursos livres e workshops curtos de 20h",
            "Aprendizado informal no trabalho",
            "Pós-graduação lato sensu generalista em Direito Civil",
        ],
        barriers=[
            "Tíquete de investimento (preço elevado para pessoa física)",
            "Disponibilidade de tempo (carga horária de 360h conciliada com trabalho)",
            "Incerteza sobre reconhecimento imediato de mercado para promoção",
        ],
        declared_vs_behavioral_notes="Interesse declarado em capacitação é alto, mas taxa de conversão depende de parcelamento acessível e grade aplicável.",
        plausible_initial_cohort_size=25,
        funnel_reach_scenario={
            "addressable_audience_reach": 5000,
            "leads_target": 250,
            "qualified_applicants_target": 60,
            "enrolled_target": 25,
            "conversion_rate_lead_to_enrolled": 0.10,
        },
        institutional_context_sources=["SUSEP - Estatísticas do Mercado Supervisionado", "CNseg - Relatório Anual"],
        institutional_multipliers_applied=False,
    )

    assert case.buyer_vs_beneficiary == "same_individual"
    assert case.segment_type == "b2c"
    assert case.plausible_initial_cohort_size == 25
    assert len(case.eligibility_criteria) == 2
    assert len(case.training_intent_signals) == 2
    assert len(case.alternatives_considered) == 3
    assert len(case.barriers) == 3
    assert case.institutional_multipliers_applied is False


def test_learner_demand_case_b2b_corporate():
    case = LearnerDemandCase(
        buyer_vs_beneficiary="employer_b2b",
        segment_type="b2b",
        eligibility_criteria=["Equipes de regulação e sinistros de seguradoras e resseguradoras"],
        training_intent_signals=["Demandas corporativas de treinamento de analistas para redução de sinistralidade"],
        alternatives_considered=["Treinamento in-company customizado", "Capacitação interna informal"],
        barriers=["Orçamento anual corporativo de T&D", "Liberação de horas dos analistas"],
        plausible_initial_cohort_size=15,
        funnel_reach_scenario={"target_companies": 10, "cohorts": 1, "students_per_cohort": 15},
        institutional_context_sources=["CNseg", "FenSeg"],
        institutional_multipliers_applied=False,
    )

    assert case.buyer_vs_beneficiary == "employer_b2b"
    assert case.segment_type == "b2b"
    assert case.plausible_initial_cohort_size == 15


def test_prohibits_direct_macro_multipliers_on_enrollment_demand():
    # Attempting to set institutional_multipliers_applied=True must raise a ValueError
    with pytest.raises(ValueError, match="dados macroeconômicos ou setoriais.*NUNCA devem ser aplicados como multiplicador direto"):
        LearnerDemandCase(
            buyer_vs_beneficiary="same_individual",
            segment_type="b2c",
            institutional_context_sources=["SUSEP"],
            institutional_multipliers_applied=True,  # VIOLATION!
        )

