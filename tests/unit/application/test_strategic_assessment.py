"""Testes unitários para parecer estratégico, SWOT e TOWS (Tarefa 4.3).

Requisitos validados:
- Schemas tipados de MarketFinding, SWOTItem, TOWSAction e StrategicAssessment.
- Rastreamento ponta a ponta: dimensão, fonte/trecho, natureza epistêmica e efeito na decisão.
- Validações determinísticas estritas em código (ADR-0003 e AGENTS.md):
  1. Lacuna de dados de pesquisa não vira fraqueza comercial do curso.
  2. Nome ENS não prova reputação ou qualidade docente do novo curso.
  3. Vaga de emprego não vira demanda de matrícula em curso.
  4. Crescimento de prêmio de seguros (SUSEP/CNseg) não vira potencial de matrícula.
  5. Ofertas da própria instituição não viram ameaça concorrente externa.
"""

from __future__ import annotations

import pytest

from prometeus.application.strategic_assessment_service import (
    StrategicAssessmentService,
    validate_data_gap_is_not_weakness,
    validate_ens_brand_does_not_prove_course_quality,
    validate_insurance_premium_growth_is_not_enrollment,
    validate_job_posting_is_not_course_demand,
    validate_own_source_is_not_external_competitor,
)
from prometeus.domain.strategic_assessment import (
    EpistemicNature,
    MarketFinding,
    StrategicAssessment,
    SWOTDimension,
    SWOTItem,
    TOWSAction,
    TOWSStrategyType,
)


def test_valid_strategic_assessment_structure():
    finding = MarketFinding(
        question_id="q-direct",
        question_text="Quais concorrentes ofertam MBA no tema?",
        finding="Existem 3 concorrentes diretos com preços entre R$ 12.000 e R$ 16.000.",
        supporting_evidence_ids=["ev-1", "ev-2"],
        counter_evidence_ids=["ev-3"],
        assumptions=["Cursos operam no formato online com encontros ao vivo"],
        materiality="high",
        alternatives_considered=["Cursos livres de curta duração"],
        remaining_gaps=["Ementa detalhada de um dos concorrentes não divulgada"],
        recommended_next_test="Solicitar contato comercial para verificar grade",
    )

    swot_item = SWOTItem(
        id="swot-1",
        dimension=SWOTDimension.STRENGTH,
        internal_or_external="internal",
        statement="Corpo docente composto por reguladores e peritos atuantes no mercado.",
        evidence_source="proposta_pedagogica",
        quote_or_datapoint="Professores convidados com atuação comprovada em seguradoras",
        epistemic_nature=EpistemicNature.OBSERVED,
        temporal_validity="atual",
        decision_effect="Diferencial prático forte contra concorrentes generalistas",
    )

    tows_action = TOWSAction(
        id="tows-1",
        strategy_type=TOWSStrategyType.SO,
        statement="Aproveitar a carência de peritos práticos destacando o corpo docente regulador.",
        action="Lançar campanha de aquisição enfatizando estudos de caso reais e análise de sinistros com os peritos.",
        responsible_area="Marketing / Comercial",
        priority="high",
    )

    assessment = StrategicAssessment(
        analysis_id="analysis-strat-1",
        market_findings=[finding],
        swot_items=[swot_item],
        tows_actions=[tows_action],
        assumptions=["Manutenção das taxas de tributação e inadimplência projetadas"],
        limitations_and_risks=["Volatilidade na disponibilidade de horários dos peritos docentes"],
    )

    assert assessment.analysis_id == "analysis-strat-1"
    assert len(assessment.market_findings) == 1
    assert assessment.swot_items[0].dimension == SWOTDimension.STRENGTH
    assert assessment.tows_actions[0].strategy_type == TOWSStrategyType.SO


def test_validator_rejects_data_gap_as_commercial_weakness():
    # Calling validate_data_gap_is_not_weakness with a data gap as WEAKNESS must raise ValueError
    bad_item = SWOTItem(
        id="swot-bad-1",
        dimension=SWOTDimension.WEAKNESS,
        internal_or_external="internal",
        statement="Ausência de dados observados sobre volume de buscas no Google Trends.",
        evidence_source="google_trends",
        quote_or_datapoint="hasData=false",
    )

    with pytest.raises(ValueError, match="Lacuna de dados de pesquisa não pode ser classificada como fraqueza comercial"):
        validate_data_gap_is_not_weakness(bad_item)


def test_validator_rejects_ens_brand_as_proof_of_course_quality():
    # Relying solely on the brand to assert faculty/academic quality without empirical evidence
    bad_item = SWOTItem(
        id="swot-bad-2",
        dimension=SWOTDimension.STRENGTH,
        internal_or_external="internal",
        statement="A reputação institucional e nome da ENS comprovam a excelente qualidade docente deste novo curso.",
        evidence_source="institucional",
        quote_or_datapoint="Marca tradicional ENS",
    )

    with pytest.raises(ValueError, match="marca ou tradição institucional não comprova"):
        validate_ens_brand_does_not_prove_course_quality(bad_item)


def test_validator_rejects_job_vacancies_as_course_demand():
    bad_finding = MarketFinding(
        question_id="q-demand",
        question_text="Existe demanda de matrículas?",
        finding="As 25 vagas de emprego no LinkedIn garantem demanda de 50 matrículas para o curso.",
        supporting_evidence_ids=["ev-job-1"],
    )

    with pytest.raises(ValueError, match="Vagas de emprego representam demanda do mercado de trabalho.*não demanda direta"):
        validate_job_posting_is_not_course_demand(bad_finding)


def test_validator_rejects_insurance_premium_growth_as_enrollment_potential():
    bad_finding = MarketFinding(
        question_id="q-market",
        question_text="Qual o potencial de mercado?",
        finding="O crescimento de 12% nos prêmios emitidos segundo a SUSEP indica potencial direto de matrículas no MBA.",
        supporting_evidence_ids=["ev-susep-1"],
    )

    with pytest.raises(ValueError, match="crescimento de prêmios emitidos no setor segurador.*não constitui potencial direto"):
        validate_insurance_premium_growth_is_not_enrollment(bad_finding)


def test_validator_rejects_own_institution_as_external_threat():
    bad_item = SWOTItem(
        id="swot-bad-3",
        dimension=SWOTDimension.THREAT,
        internal_or_external="external",
        statement="Curso similar oferecido pela própria instituição no portal ens.edu.br ameaça o lançamento.",
        evidence_source="https://ens.edu.br/cursos/extensao-seguros",
        quote_or_datapoint="Portal institucional ENS",
    )

    with pytest.raises(ValueError, match="própria instituição são contexto institucional interno e não podem ser classificados como ameaça"):
        validate_own_source_is_not_external_competitor(bad_item)


def test_strategic_assessment_service_validates_clean_assessment():
    service = StrategicAssessmentService()
    finding = MarketFinding(
        question_id="q-comp",
        question_text="Preço praticado pelos concorrentes",
        finding="Concorrentes cobram média de R$ 13.500 com parcelamento em 12x.",
        supporting_evidence_ids=["ev-1"],
    )
    swot = SWOTItem(
        id="swot-ok-1",
        dimension=SWOTDimension.OPPORTUNITY,
        internal_or_external="external",
        statement="Crescimento das exigências regulatórias sobre investigação de fraudes.",
        evidence_source="resolucao_cnsp",
        quote_or_datapoint="Circular SUSEP sobre governança de riscos",
        epistemic_nature=EpistemicNature.OBSERVED,
    )
    tows = TOWSAction(
        id="tows-ok-1",
        strategy_type=TOWSStrategyType.SO,
        statement="Alinhar matriz curricular às novas exigências da SUSEP.",
        action="Incluir módulo prático de conformidade regulatória e auditoria de sinistros.",
        responsible_area="Acadêmica",
    )

    assessment = StrategicAssessment(
        analysis_id="a-test-1",
        market_findings=[finding],
        swot_items=[swot],
        tows_actions=[tows],
    )

    # Must pass validation without exceptions
    validated = service.validate_assessment(assessment)
    assert validated.analysis_id == "a-test-1"
