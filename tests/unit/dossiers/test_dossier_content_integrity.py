import pytest
from pydantic import ValidationError

from prometeus.application.dossier_verifier import DossierVerifier
from prometeus.domain.dossiers import DossierClaim, DossierFacts, DossierOutput, DossierSection


def facts():
    return DossierFacts(
        analysis_id="a",
        course_name="Curso",
        target_audience="Gestores",
        recommendation="INSUFFICIENT_EVIDENCE",
        viability_score=35.52,
        coverage_score=0.7,
        confidence_score=0.6369,
    )


def dossier(**changes):
    values = {
        "analysis_id": "a",
        "facts_hash": facts().compute_facts_hash(),
        "executive_summary": "Análise parcial.",
        "sections": [
            DossierSection(
                section_id="exec",
                title="Diretoria",
                target_audience="executive",
                content="Análise parcial.",
                claim_ids=["c"],
            )
        ],
        "claims": [
            DossierClaim(
                claim_id="c",
                statement="Índice de viabilidade de 35,52.",
                evidence_ids=["scoring_result"],
            )
        ],
    }
    return DossierOutput(**{**values, **changes})


def test_qualitative_label_does_not_bypass_number_verification():
    claim = DossierClaim(
        claim_id="c",
        statement="Retorno de 999999%.",
        claim_type="qualitative",
        evidence_ids=["scoring_result"],
    )
    assert (
        DossierVerifier().verify_claim(claim, facts()).verification_status
        == "flagged_hallucination"
    )


@pytest.mark.parametrize("field", ["summary", "section", "title"])
def test_unsupported_numbers_in_every_visible_narrative_require_revision(field):
    doc = dossier()
    if field == "summary":
        doc.executive_summary = "Retorno de 999999%."
    elif field == "section":
        doc.sections[0].content = "Retorno de 999999%."
    else:
        doc.sections[0].title = "Retorno de 999999%."
    assert DossierVerifier().verify(doc, facts()).status == "REVISION_REQUIRED"


def test_highlight_claim_references_are_checked():
    doc = dossier(highlights={"pros": ["invented"]})
    assert DossierVerifier().verify(doc, facts()).status == "REVISION_REQUIRED"


def test_ai_cannot_mark_an_institutional_validation_as_completed():
    with pytest.raises(ValidationError):
        dossier(
            highlights={
                "validation_criteria": [
                    {
                        "criterion": "Validar preço",
                        "target": "Entrevistar interessados",
                        "claim_ids": ["c"],
                        "status": "VALIDADO",
                    }
                ]
            }
        )


def test_action_text_cannot_hide_a_fabricated_number():
    doc = dossier(
        highlights={
            "action_recommendations": [
                {
                    "area": "Comercial",
                    "action": "Garantir 999999 matrículas.",
                    "claim_ids": ["c"],
                    "priority": "high",
                }
            ]
        }
    )
    assert DossierVerifier().verify(doc, facts()).status == "REVISION_REQUIRED"


def test_old_dossier_without_highlights_remains_compatible():
    assert DossierVerifier().verify(dossier(), facts()).status == "VERIFIED"


def test_comparison_rows_must_reference_verified_claims():
    doc = dossier(highlights={"competitors": [{"label": "Concorrente", "claim_ids": ["missing"]}]})
    assert DossierVerifier().verify(doc, facts()).status == "REVISION_REQUIRED"


def test_curriculum_module_cannot_include_an_unobserved_number():
    doc = dossier(
        highlights={
            "curriculum_alignment": [
                {"module": "Módulo 999999", "need_claim_ids": ["c"], "coverage_claim_ids": ["c"]}
            ]
        }
    )
    assert DossierVerifier().verify(doc, facts()).status == "REVISION_REQUIRED"


def test_new_contract_rejects_backend_jargon_in_visible_copy():
    doc = dossier(
        schema_version=2,
        executive_summary_claim_ids=["c"],
        executive_summary="O scoring_result indica validação.",
    )
    assert DossierVerifier().verify(doc, facts()).status == "REVISION_REQUIRED"


def test_planning_numbers_are_not_market_facts():
    f = facts()
    f.research_plan = {"query": "mercado com 999999 alunos"}
    claim = DossierClaim(statement="O mercado tem 999999 alunos.", evidence_ids=["scoring_result"])
    assert DossierVerifier().verify_claim(claim, f).verification_status == "flagged_hallucination"


def test_history_reference_without_historical_facts_is_not_valid():
    claim = DossierClaim(
        statement="Histórico comprova demanda.", evidence_ids=["institutional_history"]
    )
    assert DossierVerifier().verify_claim(claim, facts()).verification_status == "unsupported"


def test_negative_growth_is_verified_with_its_sign():
    from prometeus.domain.dossiers import DossierFactItem

    f = facts()
    f.items.append(
        DossierFactItem(
            evidence_id="trend",
            source_type="TRENDS",
            title="Tendência",
            key_metrics={"growth_trend_pct": -25},
        )
    )
    claim = DossierClaim(statement="O interesse teve variação de -25%.", evidence_ids=["trend"])
    assert DossierVerifier().verify_claim(claim, f).verification_status == "verified"


def test_confidence_rounded_for_executive_display_is_authorized():
    claim = DossierClaim(statement="Confiança analítica de 64%.", evidence_ids=["scoring_result"])
    assert DossierVerifier().verify_claim(claim, facts()).verification_status == "verified"


def test_score_scale_denominator_is_allowed_but_not_an_unrelated_count():
    claim = DossierClaim(statement="O índice é de 35,52/100.", evidence_ids=["scoring_result"])
    assert DossierVerifier().verify_claim(claim, facts()).verification_status == "verified"
    unrelated = DossierClaim(
        statement="Foram observadas 100 vagas.", evidence_ids=["scoring_result"]
    )
    assert (
        DossierVerifier().verify_claim(unrelated, facts()).verification_status
        == "flagged_hallucination"
    )


def test_rejection_keeps_diagnostics_for_claim_and_visible_block():
    doc = dossier()
    doc.claims[0].statement = "Retorno garantido de 999999%."
    doc.sections[0].content = "Retorno garantido de 999999%."
    rejected = DossierVerifier().verify(doc, facts())
    assert rejected.status == "REVISION_REQUIRED"
    issues = rejected.verification_issues
    assert any(i["path"] == "claims.c" and i["code"] == "flagged_hallucination" for i in issues)
    assert next(i for i in issues if i["path"] == "claims.c")["evidence_ids"] == ["scoring_result"]
    assert any(i["path"].startswith("blocks.") for i in issues)
    assert all(len(i.get("text_excerpt", "")) <= 300 for i in issues)


def test_declared_compact_hour_unit_supports_expanded_hours_but_not_other_units():
    from prometeus.domain.dossiers import DossierFactItem

    f = facts()
    f.items.append(
        DossierFactItem(
            evidence_id="proposal",
            source_type="provided_proposal",
            title="Programa",
            summary="Modalidade on-line ao vivo. Duração 16h.",
        )
    )
    claim = DossierClaim(
        statement="A proposta informa duração de 16 horas.", evidence_ids=["proposal"]
    )
    assert DossierVerifier().verify_claim(claim, f).verification_status == "verified"
    claim = DossierClaim(
        statement="A proposta informa duração de 18 horas.", evidence_ids=["proposal"]
    )
    assert DossierVerifier().verify_claim(claim, f).verification_status == "flagged_hallucination"


def test_boolean_fact_is_not_numeric_authorization():
    from prometeus.domain.dossiers import DossierFactItem

    f = facts()
    f.items.append(
        DossierFactItem(
            evidence_id="history",
            source_type="institutional_history",
            title="Histórico",
            key_metrics={"is_synthetic": True},
        )
    )
    claim = DossierClaim(statement="Foi observada 1 matrícula.", evidence_ids=["history"])
    assert DossierVerifier().verify_claim(claim, f).verification_status == "flagged_hallucination"
