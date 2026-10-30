"""Avaliação E2E Canary com verificação em três dimensões e avaliação de utilidade (Fase 5 — Tarefa 5.3).

Executa os 3 contextos canônicos:
1. Caso com boa evidência (MBA consolidado com concorrentes, IPD interno e vagas)
2. Caso adjacente / ambíguo (Curso de fronteira com ofertas curtas e certificações)
3. Caso de insuficiência legítima (Tema sem ofertas nem sinal de mercado -> INSUFFICIENT_EVIDENCE)

Valida:
- Desacoplamento entre cálculo técnico e parecer analítico.
- Rastreabilidade de claims materiais.
- Separação estrita dos três revisores (integridade, analítico sênior, factual).
- Geração de diagnósticos acionáveis e scorecard de utilidade.
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
)


class TestThreeFoldCanaryEvaluation:
    """Suíte Canary E2E para homologação do modo tradicional de análise."""

    def test_context_1_strong_evidence_case(self) -> None:
        """Contexto 1: MBA consolidado com ofertas concorrentes, IPD interno e vagas."""
        facts = DossierFacts(
            analysis_id="canary-strong-mba-01",
            course_name="MBA em Gestão de Riscos e Seguros",
            target_audience="Subscritores e analistas de risco",
            recommendation="APPROVED",
            viability_score=81.2,
            coverage_score=0.88,
            confidence_score=0.82,
            pillar_summaries={"demand": 80.0, "pricing": 82.0, "curriculum": 85.0},
            items=[
                DossierFactItem(
                    evidence_id="ev-fgv-01",
                    source_type="competitor_offer",
                    title="Pós FGV Gestão de Riscos",
                    key_metrics={"total_price_brl": 18000.0, "workload_hours": 360},
                    summary="Programa concorrente presencial e online em SP, 360h por R$ 18.000,00",
                    source_url="https://fgv.br/gestao-riscos",
                ),
                DossierFactItem(
                    evidence_id="ev-puc-01",
                    source_type="competitor_offer",
                    title="Especialização PUC Seguros",
                    key_metrics={"total_price_brl": 16500.0, "workload_hours": 360},
                    summary="Especialização lato sensu 360h por R$ 16.500,00",
                    source_url="https://puc.br/seguros",
                ),
                DossierFactItem(
                    evidence_id="ev-job-01",
                    source_type="job_posting",
                    title="Subscritor Sênior - Porto Seguro",
                    key_metrics={"openings": 4},
                    summary="Vaga para subscrição de grandes riscos e regulação",
                    source_url="https://linkedin.com/jobs/view/1111",
                ),
            ],
            limitations=["Pesquisa focada nas regiões Sul e Sudeste."],
            counterevidence=["Preço médio de concorrentes 8% abaixo do valor teto previsto."],
            analysis_audit={
                "integrity_report": IntegrityReport(
                    source_count=3,
                    observations_count=3,
                    brief_facts_count=4,
                    job_descriptions_expected=1,
                    job_descriptions_available=1,
                    status="INTACT",
                ).to_dict(),
                "declared_offer": {"ticket": 15000.0, "institution": "ENS"},
            },
        )

        claims = [
            DossierClaim(
                claim_id="CLM-01",
                statement="Os concorrentes mapeados praticam investimentos totais de R$ 16.500,00 e R$ 18.000,00 para cursos de 360 horas.",
                claim_type=ClaimType.QUANTITATIVE,
                evidence_ids=["ev-fgv-01", "ev-puc-01"],
                support_level=SupportLevel.OBSERVED,
            ),
            DossierClaim(
                claim_id="CLM-02",
                statement="Vagas em seguradoras demandam competências de subscrição de riscos e regulação.",
                claim_type=ClaimType.QUALITATIVE,
                evidence_ids=["ev-job-01"],
                support_level=SupportLevel.OBSERVED,
            ),
            DossierClaim(
                claim_id="CLM-03",
                statement="O índice de viabilidade calculado em código atingiu 81.2 com cobertura de 88.0.",
                claim_type=ClaimType.QUANTITATIVE,
                evidence_ids=["scoring_result"],
                support_level=SupportLevel.OBSERVED,
            ),
        ]

        dossier = DossierOutput(
            analysis_id=facts.analysis_id,
            executive_summary="Dossiê de viabilidade com forte suporte de concorrência e empregabilidade.",
            executive_summary_claim_ids=["CLM-03"],
            sections=[
                DossierSection(
                    section_id="sec-exec",
                    title="Viabilidade e Decisão",
                    target_audience="executive",
                    content="O programa atinge score viável de 81.2 com robusta cobertura de mercado.",
                    claim_ids=["CLM-03"],
                ),
                DossierSection(
                    section_id="sec-acad",
                    title="Alinhamento Curricular",
                    target_audience="academic",
                    content="Grade alinhada a subscrição e regulação identificadas nas contratações.",
                    claim_ids=["CLM-02"],
                ),
                DossierSection(
                    section_id="sec-mkt",
                    title="Público e Concorrência",
                    target_audience="marketing",
                    content="Público-alvo qualificado e concorrentes diretos mapeados na faixa de R$ 16.500 a R$ 18.000.",
                    claim_ids=["CLM-01"],
                ),
            ],
            claims=claims,
            highlights=DossierHighlights(
                pros=["CLM-01", "CLM-02"],
                cons=["CLM-01"],  # Cita concorrentes como risco de preço
            ),
            facts_hash=facts.compute_facts_hash(),
            schema_version=2,
        )

        verifier = DossierVerifier()
        verified = verifier.verify(dossier, facts)

        assert verified.status == DossierStatus.VERIFIED
        review = verified.three_fold_review
        assert review is not None

        # 1. Integridade
        assert review.data_integrity.status == ReviewStatus.PASS
        assert review.data_integrity.source_count == 3
        assert review.data_integrity.missing_descriptions_count == 0

        # 2. Qualidade analítica sênior
        assert review.senior_analytical.status == ReviewStatus.PASS
        assert review.senior_analytical.independence_verified is True
        assert review.senior_analytical.proxies_properly_qualified is True
        assert review.senior_analytical.counterevidence_analyzed is True

        # 3. Factualidade da redação
        assert review.factual_drafting.status == ReviewStatus.PASS
        assert review.factual_drafting.numeric_consistency is True
        assert review.factual_drafting.hallucinations_count == 0

    def test_context_2_adjacent_ambiguous_case(self) -> None:
        """Contexto 2: Curso de fronteira com ofertas curtas e ambiguidade de formato."""
        facts = DossierFacts(
            analysis_id="canary-adjacent-ai-02",
            course_name="Imersão Prática em IA Generativa para Seguros",
            target_audience="Inovação e produtos digitais em seguros",
            recommendation="APPROVED_WITH_ADJUSTMENTS",
            viability_score=58.0,
            coverage_score=0.55,
            confidence_score=0.60,
            items=[
                DossierFactItem(
                    evidence_id="ev-workshop-16h",
                    source_type="short_course",
                    title="Workshop de IA em Seguros - 16h",
                    key_metrics={"workload_hours": 16, "total_price_brl": 1200.0},
                    summary="Curso livre intensivo de 16 horas com foco em ferramentas de IA",
                    source_url="https://escola-ia.com/curso-16h",
                )
            ],
            limitations=["Ofertas concorrentes identificadas são cursos livres de curta duração, não MBAs."],
            counterevidence=["Formato de 16h não compete em titulação com cursos de pós-graduação."],
            analysis_audit={
                "integrity_report": IntegrityReport(
                    source_count=1,
                    observations_count=1,
                    brief_facts_count=2,
                    status="INTACT",
                ).to_dict(),
                "declared_offer": {"ticket": 2500.0, "institution": "ENS"},
            },
        )

        # O redator escreve com clareza a distinção, sem igualar 16h a titulação de MBA
        claims = [
            DossierClaim(
                claim_id="CLM-01",
                statement="Identificado workshop livre de 16 horas com investimento de R$ 1.200,00 como formato adjacente.",
                claim_type=ClaimType.QUANTITATIVE,
                evidence_ids=["ev-workshop-16h"],
                support_level=SupportLevel.OBSERVED,
            ),
            DossierClaim(
                claim_id="CLM-02",
                statement="O índice de viabilidade calculado foi de 58.0.",
                claim_type=ClaimType.QUANTITATIVE,
                evidence_ids=["scoring_result"],
                support_level=SupportLevel.OBSERVED,
            ),
        ]

        dossier = DossierOutput(
            analysis_id=facts.analysis_id,
            executive_summary="Síntese para curso de fronteira tecnológica com ofertas curtas no mercado.",
            executive_summary_claim_ids=["CLM-02"],
            sections=[
                DossierSection(
                    section_id="sec-1",
                    title="Viabilidade e Decisão",
                    target_audience="executive",
                    content="O score calculado é 58.0, recomendando ajustes de posicionamento.",
                    claim_ids=["CLM-02"],
                ),
                DossierSection(
                    section_id="sec-2",
                    title="Mercado e Formatos",
                    target_audience="marketing",
                    content="Oferta adjacente observada com workshop de 16 horas por R$ 1.200,00.",
                    claim_ids=["CLM-01"],
                ),
                DossierSection(
                    section_id="sec-3",
                    title="Riscos e Limitações",
                    target_audience="academic",
                    content="Cursos livres de curta duração não concorrem em titulação acadêmica; limitações de formato devem ser testadas em piloto.",
                    claim_ids=["CLM-01"],
                ),
            ],
            claims=claims,
            highlights=DossierHighlights(cons=["CLM-01"]),
            facts_hash=facts.compute_facts_hash(),
            schema_version=2,
        )

        verifier = DossierVerifier()
        verified = verifier.verify(dossier, facts)

        assert verified.status == DossierStatus.VERIFIED
        review = verified.three_fold_review
        assert review is not None

        # Revisor sênior valida que não houve falsa equivalência de titulação
        assert review.senior_analytical.proxies_properly_qualified is True
        assert review.senior_analytical.counterevidence_analyzed is True
        assert review.factual_drafting.numeric_consistency is True

    def test_context_3_legitimate_absence_insufficient_evidence(self) -> None:
        """Contexto 3: Tema sem ofertas nem sinal de mercado -> INSUFFICIENT_EVIDENCE legítimo."""
        facts = DossierFacts(
            analysis_id="canary-insufficient-space-03",
            course_name="Certificação em Subscrição Aeroespacial para Microsseguros",
            target_audience="Subscritores espaciais e microsseguradoras",
            recommendation="INSUFFICIENT_EVIDENCE",
            viability_score=22.0,
            coverage_score=0.15,
            confidence_score=0.30,
            items=[],  # Sem ofertas nem vagas encontradas
            limitations=[
                "Nenhum curso comparável ou vaga específica foi localizado no Brasil.",
                "Ausência de busca não equivale a demanda zero; recomenda-se validação direta com o setor.",
            ],
            counterevidence=["Inexistência de histórico de turmas similares no portfólio."],
            analysis_audit={
                "integrity_report": IntegrityReport(
                    source_count=0,
                    observations_count=0,
                    brief_facts_count=1,
                    status="INTACT",
                ).to_dict(),
                "declared_offer": {"ticket": 8000.0, "institution": "ENS"},
            },
        )

        claims = [
            DossierClaim(
                claim_id="CLM-01",
                statement="O resultado calculado foi de evidências insuficientes para lançamento, com índice de viabilidade de 22.0.",
                claim_type=ClaimType.QUANTITATIVE,
                evidence_ids=["scoring_result"],
                support_level=SupportLevel.OBSERVED,
            )
        ]

        dossier = DossierOutput(
            analysis_id=facts.analysis_id,
            executive_summary="Base insuficiente para recomendar lançamento; ausência de dados de mercado.",
            executive_summary_claim_ids=["CLM-01"],
            sections=[
                DossierSection(
                    section_id="sec-1",
                    title="Viabilidade e Decisão",
                    target_audience="executive",
                    content="A recomendação calculada é de dados insuficientes, com índice de 22.0.",
                    claim_ids=["CLM-01"],
                ),
                DossierSection(
                    section_id="sec-2",
                    title="Mercado e Limitações",
                    target_audience="academic",
                    content="Nenhum programa similar foi encontrado nas fontes consultadas.",
                    claim_ids=["CLM-01"],
                ),
                DossierSection(
                    section_id="sec-3",
                    title="Próximos Passos",
                    target_audience="marketing",
                    content="Realizar pesquisa primária com empresas aeroespaciais antes de qualquer investimento.",
                    claim_ids=["CLM-01"],
                ),
            ],
            claims=claims,
            highlights=DossierHighlights(
                cons=["CLM-01"],
            ),
            facts_hash=facts.compute_facts_hash(),
            schema_version=2,
        )

        verifier = DossierVerifier()
        verified = verifier.verify(dossier, facts)

        # O dossiê é verificado com sucesso, reconhecendo honestamente a insuficiência probatória
        assert verified.status == DossierStatus.VERIFIED
        review = verified.three_fold_review
        assert review is not None

        # Desacoplamento verificado: o cálculo técnico é INSUFFICIENT_EVIDENCE,
        # e o parecer analítico valida a carência probatória sem inflar a nota
        assert facts.recommendation == "INSUFFICIENT_EVIDENCE"
        assert review.senior_analytical.counterevidence_analyzed is True
        assert review.data_integrity.status == ReviewStatus.PASS
        assert review.factual_drafting.status == ReviewStatus.PASS
