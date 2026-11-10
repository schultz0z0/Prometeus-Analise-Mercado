"""Testes unitários do construtor determinístico das 9 subpáginas do CMS do Dossiê e verificação no DossierVerifier."""

from __future__ import annotations

from types import SimpleNamespace

from prometeus.application.dossier_cms_builder import (
    CMS_TAB_ORDER,
)
from prometeus.application.dossier_verifier import DossierVerifier
from prometeus.application.synthesize_dossier import DossierSynthesisService
from prometeus.domain.dossiers import (
    DossierAction,
    DossierClaim,
    DossierFactItem,
    DossierFacts,
    DossierHighlights,
    DossierOutput,
    DossierValidationCriterion,
)


def _sample_fixtures() -> tuple[SimpleNamespace, SimpleNamespace, DossierFacts, DossierOutput]:
    institution_ctx = {
        "id": "ens",
        "name": "Escola de Negócios e Seguros",
        "domains": ["ens.edu.br"],
        "competitors": [
            {
                "id": "ibmec",
                "name": "Ibmec",
                "category": "executive_business",
                "domains": ["ibmec.br"],
                "focus_notes": "MBAs executivos em Finanças e Riscos.",
                "social": {"instagram_handle": "ibmec", "linkedin_scope": "national"},
            },
            {
                "id": "fgv",
                "name": "FGV Educação Executiva",
                "category": "executive_business",
                "domains": ["fgv.br"],
                "focus_notes": "MBAs executivos em Seguros e Previdência.",
                "social": {"instagram_handle": "fgv.oficial", "linkedin_scope": "national"},
            },
        ],
        "sector_radar": [
            {
                "id": "porto-seguro",
                "name": "Porto Seguro",
                "priority": "primary",
                "domains": ["portoseguro.com.br"],
                "monitoring_focus": ["IA e telemetria", "corretores"],
                "social": {"instagram_handle": "porto", "linkedin_scope": "national"},
            },
        ],
    }

    analysis = SimpleNamespace(
        id="anl-cms-01",
        tenant_id="ens",
        course_name="MBA em Inteligência Artificial para Seguros",
        proposal_data={
            "ticket": 12000.0,
            "price_period": "total",
            "workload_hours": 360,
            "modality": "EAD Live",
            "_institution_context": institution_ctx,
        },
    )
    scoring = SimpleNamespace(
        viability_score=78.4,
        coverage_score=0.88,
        confidence_score=0.80,
        recommendation="APPROVED_WITH_ADJUSTMENTS",
    )
    facts = DossierFacts(
        analysis_id="anl-cms-01",
        course_name="MBA em Inteligência Artificial para Seguros",
        target_audience="Gestores e Especialistas em Seguros",
        recommendation="APPROVED_WITH_ADJUSTMENTS",
        viability_score=78.4,
        coverage_score=0.88,
        confidence_score=0.80,
        pillar_summaries={
            "internal_history": 86.0,
            "paid_competition": 72.0,
            "search_and_media": 82.0,
            "employability": 79.0,
            "syllabus_fit": 84.0,
            "pricing": 68.0,
        },
        pillar_details={
            "internal_history": {"is_present": True, "evidence_count": 3},
            "paid_competition": {"is_present": True, "evidence_count": 4},
            "search_and_media": {"is_present": True, "evidence_count": 5},
            "employability": {"is_present": True, "evidence_count": 3},
            "syllabus_fit": {"is_present": True, "evidence_count": 2},
            "pricing": {"is_present": True, "evidence_count": 2},
        },
        items=[
            DossierFactItem(
                evidence_id="ev-ibmec-01",
                source_type="OFFER",
                title="MBA Executivo em Finanças e Riscos — Ibmec",
                key_metrics={
                    "actor_role": "configured_competitor",
                    "matched_actor_id": "ibmec",
                    "matched_actor_name": "Ibmec",
                    "competition_relation": "direct",
                    "price_brl": 14900.0,
                    "workload_hours": 360,
                },
                summary="Oferta ativa Online (EAD) com foco executivo.",
                source_url="https://pos.ibmec.br/mba-financas-riscos",
            ),
            DossierFactItem(
                evidence_id="ev-radar-porto",
                source_type="SOCIAL_MEDIA",
                title="Porto Seguro investe em IA generativa para sinistros",
                key_metrics={
                    "evidence_role": "context_only",
                    "actor_role": "sector_radar",
                    "matched_actor_id": "porto-seguro",
                    "matched_actor_name": "Porto Seguro",
                    "actor_priority": "primary",
                },
                summary="Aceleração de uso de IA generativa na jornada do corretor e sinistros.",
                source_url="https://linkedin.com/company/porto/posts/1",
            ),
            DossierFactItem(
                evidence_id="ev-jobs-01",
                source_type="JOB_MARKET",
                title="Vagas de Especialista em IA e Seguros",
                key_metrics={"open_jobs_count": 28, "salary_median_brl": 14500.0},
                summary="Demanda aquecida por especialistas em automação de subscrição e sinistros.",
                source_url="https://linkedin.com/jobs/search",
            ),
        ],
        limitations=["Premissas completas de CAC e custos fixos não informadas na proposta."],
        analysis_audit={
            "pricing": {
                "comparables_count": 1,
                "mean_total_brl": 14900.0,
                "comparables": [
                    {
                        "title": "MBA Executivo em Finanças e Riscos — Ibmec",
                        "total_brl": 14900.0,
                        "evidence_ids": ["ev-ibmec-01"],
                    }
                ],
            },
            "internal_audit": {
                "comparables_count": 2,
                "mean_students": 44.0,
                "mean_evasion_rate": 0.08,
                "comparables": [
                    {
                        "course_name": "MBA em Gestão de Seguros e Resseguros",
                        "students_count": 48,
                        "evasion_rate": 0.07,
                    },
                    {
                        "course_name": "Pós em Subscrição e Riscos",
                        "students_count": 40,
                        "evasion_rate": 0.09,
                    },
                ],
            },
        },
    )
    dossier = DossierOutput(
        analysis_id="anl-cms-01",
        facts_hash=facts.compute_facts_hash(),
        executive_summary="O curso apresenta forte aderência histórica e demanda profissional consistente, exigindo validação das premissas financeiras da turma.",
        executive_summary_claim_ids=["CLM-1", "CLM-2"],
        claims=[
            DossierClaim(
                claim_id="CLM-1",
                statement="Foram identificadas 28 vagas abertas em IA e Seguros com mediana salarial de R$ 14.500,00.",
                evidence_ids=["ev-jobs-01"],
            ),
            DossierClaim(
                claim_id="CLM-2",
                statement="O Ibmec oferta MBA correlato a R$ 14.900,00 com carga horária de 360 horas.",
                evidence_ids=["ev-ibmec-01"],
            ),
        ],
        highlights=DossierHighlights(
            pros=["CLM-1"],
            cons=["CLM-2"],
            action_recommendations=[
                DossierAction(
                    area="product",
                    action="Estruturar módulos práticos de IA aplicada a sinistros e subscrição.",
                    claim_ids=["CLM-1"],
                    priority="high",
                ),
                DossierAction(
                    area="commercial",
                    action="Posicionar o ticket de R$ 12.000 abaixo da referência observada de R$ 14.900.",
                    claim_ids=["CLM-2"],
                    priority="medium",
                ),
            ],
            validation_criteria=[
                DossierValidationCriterion(
                    criterion="Confirmar custos fixos e CAC da turma antes do lançamento comercial.",
                    target="Viabilidade financeira",
                    claim_ids=["CLM-2"],
                )
            ],
        ),
    )
    return analysis, scoring, facts, dossier


def test_build_cms_dossier_pages_returns_all_nine_subpages_and_respects_deterministic_rules() -> None:
    analysis, scoring, facts, dossier = _sample_fixtures()
    presentation = DossierSynthesisService._build_visual_presentation_blocks(
        analysis, scoring, facts, dossier
    )

    assert "cms_pages" in presentation
    cms_pages = presentation["cms_pages"]
    assert cms_pages["schema_version"] == 1
    assert cms_pages["default_tab"] == "overview"
    assert [tab["id"] for tab in cms_pages["tabs"]] == list(CMS_TAB_ORDER)
    assert list(CMS_TAB_ORDER) == [
        "overview",
        "key_metrics",
        "fixed_competition",
        "sector_radar",
        "economics",
        "swot_tows",
        "viability_pillars",
        "revisions",
        "sources_evidences",
    ]

    pages = cms_pages["pages"]
    for tab_id in CMS_TAB_ORDER:
        assert tab_id in pages

    # 1. Overview checks
    overview = pages["overview"]
    assert overview["ivo_score"] == 78
    assert overview["ie_score"] == 84  # round((0.88 + 0.80) / 2 * 100)
    assert overview["recommendation_code"] == "APPROVED_WITH_ADJUSTMENTS"
    assert len(overview["decision_matrix"]) == 6

    # 2. Missing financial assumptions must never be fabricated
    economics_page = pages["economics"]
    assert economics_page["status"] == "assumptions_required"
    assert any(
        "premissa" in kpi["value"].lower() or "premissa" in kpi["badge"].lower()
        for kpi in economics_page["kpis"]
    )

    # 3. Fixed competition maps observed competitor & positioning 2x2
    comp_page = pages["fixed_competition"]
    assert comp_page["monitored_total"] == 2
    assert comp_page["offers_found_count"] == 1
    assert len(comp_page["positioning_map"]["points"]) >= 1

    # 4. Viability pillars has all 6 official portfolio-v2 pillars
    pillars_page = pages["viability_pillars"]
    assert len(pillars_page["pillar_cards"]) == 6
    weights_sum = sum(card["weight_pct"] for card in pillars_page["pillar_cards"])
    assert weights_sum == 100


def test_dossier_verifier_validates_cms_pages_and_blocks_tampering() -> None:
    analysis, scoring, facts, dossier = _sample_fixtures()
    presentation = DossierSynthesisService._build_visual_presentation_blocks(
        analysis, scoring, facts, dossier
    )
    verifier = DossierVerifier()

    issues = verifier.verify_presentation(
        dossier=dossier,
        facts=facts,
        presentation=presentation,
        proposal=analysis.proposal_data,
    )
    assert issues == []

    # Tamper with an IVO score inside cms_pages
    tampered = dict(presentation)
    tampered["cms_pages"] = dict(presentation["cms_pages"])
    tampered["cms_pages"]["pages"] = dict(presentation["cms_pages"]["pages"])
    tampered_overview = dict(presentation["cms_pages"]["pages"]["overview"])
    tampered_overview["ivo_score"] = 99
    tampered["cms_pages"]["pages"]["overview"] = tampered_overview

    tampered_issues = verifier.verify_presentation(
        dossier=dossier,
        facts=facts,
        presentation=tampered,
        proposal=analysis.proposal_data,
    )
    assert any(issue["path"] == "presentation.cms_pages" for issue in tampered_issues)
