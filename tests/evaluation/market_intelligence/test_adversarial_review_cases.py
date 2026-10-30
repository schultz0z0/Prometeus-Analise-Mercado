"""Casos adversariais para homologação do redator e revisores (Fase 5 — Tarefa 5.2).

Cobre especificamente:
1. Redator certo / revisor errado (tolerância a formatações válidas e não-rejeição de fatos comprovados).
2. Redator errado / revisor certo (detecção de alucinações numéricas, injeção e extrapolação de proxies).
3. Base incompleta / revisor factual satisfeito (dados ausentes produzem alerta/pendência no parecer sênior
   sem aprovação tácita, mesmo quando o redator não alucina).
"""

from __future__ import annotations

from prometeus.application.dossier_verifier import DossierVerifier
from prometeus.domain.dossiers import (
    ClaimType,
    DossierClaim,
    DossierFactItem,
    DossierFacts,
    DossierHighlights,
    DossierOutput,
    DossierSection,
    DossierStatus,
    IntegrityReport,
    ReviewStatus,
    SupportLevel,
    VerificationStatus,
)


def make_base_facts(
    *,
    analysis_id: str = "adv-test-01",
    include_pricing: bool = True,
) -> DossierFacts:
    items = []
    if include_pricing:
        items.append(
            DossierFactItem(
                evidence_id="ev-fgv-direito",
                source_type="competitor_offer",
                title="Pós-Graduação FGV Direito Securitário",
                key_metrics={
                    "total_price_brl": 20700.0,
                    "installments": 18,
                    "installment_price_brl": 1150.0,
                    "workload_hours": 360,
                },
                summary="Curso com 360h por 18 parcelas de R$ 1.150,00 totalizando R$ 20.700,00",
                source_url="https://fgv.br/direito-securitario",
            )
        )
    items.append(
        DossierFactItem(
            evidence_id="ev-job-sinistros",
            source_type="job_posting",
            title="Analista de Sinistros Pleno",
            key_metrics={"openings": 2},
            summary="Vaga para regulação de sinistros em transportes e responsabilidade civil",
            source_url="https://linkedin.com/jobs/view/9999",
        )
    )

    return DossierFacts(
        analysis_id=analysis_id,
        course_name="MBA em Gestão Jurídica de Seguros",
        target_audience="Advogados e gestores de sinistros",
        recommendation="APPROVED" if include_pricing else "INSUFFICIENT_EVIDENCE",
        viability_score=72.0 if include_pricing else 35.0,
        coverage_score=0.8 if include_pricing else 0.4,
        confidence_score=0.75 if include_pricing else 0.5,
        items=items,
        limitations=["Dados de precificação incompletos fora de SP"] if not include_pricing else [],
        counterevidence=[],
        analysis_audit={
            "integrity_report": IntegrityReport(
                source_count=len(items),
                observations_count=len(items),
                brief_facts_count=len(items) + 1,
                status="INTACT",
            ).to_dict(),
            "declared_offer": {"ticket": 15000.0, "institution": "ENS"},
        },
    )


class TestAdversarialReviewCases:
    """Suíte adversarial de testes entre redator e revisores especializados."""

    def test_case_1_redator_certo_revisor_errado(self) -> None:
        """Caso 1: Redator certo / revisor errado.

        O redator redige com números reais (R$ 20.700,00 e 18x de 1.150,00 e 360 horas)
        e formatações brasileiras legítimas.
        O verificador calibrado NÃO deve rejeitar nem classificar como alucinação.
        """
        facts = make_base_facts(include_pricing=True)
        claim = DossierClaim(
            claim_id="CLM-01",
            statement="A pós-graduação concorrente possui carga horária de 360 horas e investimento total de R$ 20.700,00 em 18 parcelas de 1150.0.",
            claim_type=ClaimType.QUANTITATIVE,
            evidence_ids=["ev-fgv-direito"],
            support_level=SupportLevel.OBSERVED,
        )
        dossier = DossierOutput(
            analysis_id=facts.analysis_id,
            executive_summary="Síntese da análise com preços de mercado observados.",
            executive_summary_claim_ids=["CLM-01"],
            sections=[
                DossierSection(
                    section_id="sec-1",
                    title="Concorrência",
                    target_audience="executive",
                    content="A concorrente oferece o programa por R$ 20.700,00 em 18 parcelas.",
                    claim_ids=["CLM-01"],
                )
            ],
            claims=[claim],
            highlights=DossierHighlights(),
            facts_hash=facts.compute_facts_hash(),
            schema_version=2,
        )

        verifier = DossierVerifier()
        drafting_review = verifier.verify_factual_drafting(dossier, facts)

        # O redator estava certo: o revisor NÃO deve disparar alucinação nem rejeição
        assert drafting_review.status == ReviewStatus.PASS
        assert drafting_review.numeric_consistency is True
        assert drafting_review.hallucinations_count == 0
        assert claim.verification_status == VerificationStatus.VERIFIED

    def test_case_2_redator_errado_revisor_certo(self) -> None:
        """Caso 2: Redator errado / revisor certo.

        O redator tenta extrapolar uma vaga para 'garantia de 50 matrículas'
        ou inventa um número de alunos não existente na base.
        O revisor deve detectar a infração imediatamente e exigir revisão.
        """
        facts = make_base_facts(include_pricing=True)
        # Redator tenta afirmar que vaga vira matrícula garantida e inventa número 50
        claim = DossierClaim(
            claim_id="CLM-01",
            statement="As vagas abertas garantem a matrícula direta de 50 novos alunos no curso.",
            claim_type=ClaimType.STRATEGIC,
            evidence_ids=["ev-job-sinistros"],
            support_level=SupportLevel.OBSERVED,
        )
        dossier = DossierOutput(
            analysis_id=facts.analysis_id,
            executive_summary="Síntese que promete matrículas com base em vagas.",
            executive_summary_claim_ids=["CLM-01"],
            sections=[
                DossierSection(
                    section_id="sec-1",
                    title="Demanda",
                    target_audience="executive",
                    content="Projeção de 50 matrículas diretas garantidas.",
                    claim_ids=["CLM-01"],
                )
            ],
            claims=[claim],
            highlights=DossierHighlights(),
            facts_hash=facts.compute_facts_hash(),
            schema_version=2,
        )

        verifier = DossierVerifier()
        verified = verifier.verify(dossier, facts)

        assert verified.status == DossierStatus.REVISION_REQUIRED
        review = verified.three_fold_review
        assert review is not None

        # Revisor factual pega a alucinação numérica do '50'
        assert review.factual_drafting.status == ReviewStatus.FAIL
        assert review.factual_drafting.hallucinations_count >= 1

        # Revisor sênior pega a extrapolação do proxy (vaga não é matrícula garantida)
        assert review.senior_analytical.status == ReviewStatus.FAIL
        assert review.senior_analytical.proxies_properly_qualified is False
        assert any("vaga" in iss["message"].lower() for iss in review.senior_analytical.issues)

    def test_case_3_base_incompleta_revisor_factual_satisfeito(self) -> None:
        """Caso 3: Base incompleta / revisor factual satisfeito.

        A base coletada NÃO tem preços de concorrentes.
        O redator factual é honesto: escreve que preços não foram encontrados e cita apenas a vaga.
        O revisor factual fica satisfeito (zero alucinações).
        PORÉM, o revisor sênior / integridade sinaliza que perguntas críticas de decisão
        (economics_and_pricing ou cobertura) estão incompletas, emitindo recomendações acionáveis.
        """
        facts = make_base_facts(include_pricing=False)
        claim = DossierClaim(
            claim_id="CLM-01",
            statement="Vaga observada para analista de sinistros em seguradoras.",
            claim_type=ClaimType.QUALITATIVE,
            evidence_ids=["ev-job-sinistros"],
            support_level=SupportLevel.OBSERVED,
        )
        dossier = DossierOutput(
            analysis_id=facts.analysis_id,
            executive_summary="Análise preliminar; ausência de preços de concorrentes observados.",
            executive_summary_claim_ids=["CLM-01"],
            sections=[
                DossierSection(
                    section_id="sec-1",
                    title="Alinhamento Profissional",
                    target_audience="academic",
                    content="Vagas observadas no mercado profissional.",
                    claim_ids=["CLM-01"],
                )
            ],
            claims=[claim],
            highlights=DossierHighlights(),
            facts_hash=facts.compute_facts_hash(),
            schema_version=2,
        )

        verifier = DossierVerifier()
        drafting_review = verifier.verify_factual_drafting(dossier, facts)
        analytical_review = verifier.verify_senior_analytical_quality(dossier, facts)

        # 1. Revisor factual está plenamente satisfeito (não houve alucinação)
        assert drafting_review.status == ReviewStatus.PASS
        assert drafting_review.numeric_consistency is True
        assert drafting_review.no_hallucinations is True

        # 2. Revisor sênior detecta que perguntas-chave ficaram descobertas (competitors, pricing)
        assert analytical_review.status in (ReviewStatus.WARN, ReviewStatus.FAIL)
        assert analytical_review.question_coverage["competitors"] is False
        assert analytical_review.question_coverage["economics_and_pricing"] is False
        # Emite diagnóstico acionável sem culpar o redator
        assert len(analytical_review.actionable_recommendations) >= 1
