"""Testes unitários para modelos de domínio e cálculo de hash canônico do dossiê."""

from prometeus.domain.dossiers import (
    ClaimType,
    DossierClaim,
    DossierFactItem,
    DossierFacts,
    DossierOutput,
    DossierSection,
    DossierStatus,
    SupportLevel,
    VerificationStatus,
)


def test_dossier_facts_hash_determinism() -> None:
    facts1 = DossierFacts(
        analysis_id="an-123",
        course_name="MBA em Inteligência Artificial em Seguros",
        target_audience="Líderes de Sinistros",
        recommendation="APPROVED",
        viability_score=84.5,
        coverage_score=1.0,
        confidence_score=0.92,
        pillar_summaries={"internal_history": 85.0, "search_and_media": 90.0},
        items=[
            DossierFactItem(
                evidence_id="ev-01",
                source_type="market_evidence",
                title="Google Ads Volume",
                key_metrics={"volume": 3200},
            ),
            DossierFactItem(
                evidence_id="ev-02",
                source_type="market_evidence",
                title="Média Salarial",
                key_metrics={"salary_median_brl": 14000.0},
            ),
        ],
        limitations=["Pilar pricing com cobertura parcial"],
    )

    facts2 = DossierFacts(
        analysis_id="an-123",
        course_name="MBA em Inteligência Artificial em Seguros",
        target_audience="Líderes de Sinistros",
        recommendation="APPROVED",
        viability_score=84.5,
        coverage_score=1.0,
        confidence_score=0.92,
        pillar_summaries={"search_and_media": 90.0, "internal_history": 85.0},  # ordem invertida
        items=[
            DossierFactItem(
                evidence_id="ev-02",
                source_type="market_evidence",
                title="Média Salarial",
                key_metrics={"salary_median_brl": 14000.0},
            ),
            DossierFactItem(
                evidence_id="ev-01",
                source_type="market_evidence",
                title="Google Ads Volume",
                key_metrics={"volume": 3200},
            ),
        ],
        limitations=["Pilar pricing com cobertura parcial"],
    )

    # Hashes devem ser idênticos independente da ordem dos elementos
    assert facts1.compute_facts_hash() == facts2.compute_facts_hash()
    assert len(facts1.compute_facts_hash()) == 64


def test_dossier_output_structure_and_lookup() -> None:
    claim = DossierClaim(
        claim_id="CLM-01",
        statement="O curso possui 3.200 buscas mensais estimadas no Google Ads.",
        claim_type=ClaimType.QUANTITATIVE,
        evidence_ids=["ev-01"],
        support_level=SupportLevel.OBSERVED,
        verification_status=VerificationStatus.VERIFIED,
    )

    sec = DossierSection(
        section_id="exec_summary",
        title="Resumo Executivo",
        target_audience="executive",
        content="Resumo estratégico.",
        claim_ids=["CLM-01"],
    )

    dossier = DossierOutput(
        analysis_id="an-123",
        prompt_version="dossier-v1",
        model_name="gpt-4o-mini",
        executive_summary="Resumo estratégico.",
        sections=[sec],
        claims=[claim],
        facts_hash="hash123",
        status=DossierStatus.VERIFIED,
    )

    assert dossier.get_claim("CLM-01") is not None
    assert dossier.get_claim("CLM-99") is None
    assert dossier.claims[0].claim_type == ClaimType.QUANTITATIVE
