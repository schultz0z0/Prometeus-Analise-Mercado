from prometeus.application.dossier_verifier import DossierVerifier
from prometeus.domain.dossiers import DossierClaim, DossierFacts


def test_scoring_reference_contains_interpretation_and_values_in_one_citable_source():
    facts = DossierFacts(
        analysis_id="a",
        course_name="Curso",
        target_audience="Profissionais",
        recommendation="INSUFFICIENT_EVIDENCE",
        viability_score=55.39,
        coverage_score=0.8,
        confidence_score=0.6198,
        scoring_experimental=True,
    )
    source = facts.get_fact_item("scoring_result")
    assert source.source_type == "computed_scoring"
    assert source.key_metrics["scoring_experimental"] is True
    assert source.key_metrics["recommendation"] == "INSUFFICIENT_EVIDENCE"
    assert "probabilidade de sucesso" in source.summary
    assert "mercado pesquisado" in source.summary
    assert source.to_dict() in [i.to_dict() for i in facts.citable_items()]
    claim = DossierClaim(
        statement="O índice experimental é 55,39, a cobertura de evidências é 80% e a confiança analítica é 61,98%.",
        evidence_ids=["scoring_result"],
    )
    assert DossierVerifier().verify_claim(claim, facts).verification_status == "verified"


def test_provider_schema_forbids_empty_or_invented_evidence_references():
    from prometeus.application.dossier_generation_contract import dossier_json_schema

    schema = dossier_json_schema(["scoring_result", "institutional_history"])
    assert schema["additionalProperties"] is False
    claim = schema["properties"]["claims"]["items"]
    refs = claim["properties"]["evidence_ids"]
    assert refs["minItems"] == 1
    assert refs["items"]["enum"] == ["institutional_history", "scoring_result"]
    assert "evidence_ids" in claim["required"]
    assert claim["additionalProperties"] is False


def test_canonical_source_changes_are_part_of_facts_hash():
    facts = DossierFacts(
        analysis_id="a",
        course_name="Curso",
        target_audience="Público",
        recommendation="INSUFFICIENT_EVIDENCE",
        viability_score=55.39,
        coverage_score=0.8,
        confidence_score=0.6198,
    )
    before = facts.compute_facts_hash()
    facts.scoring_experimental = False
    assert facts.compute_facts_hash() != before
    assert "experimental" not in facts.get_fact_item("scoring_result").summary


def test_provider_schema_constrains_every_claim_reference_including_pros_and_cons():
    from prometeus.application.dossier_generation_contract import dossier_json_schema

    schema = dossier_json_schema(["scoring_result"], claim_ids=["CLM-01", "CLM-02"])
    props = schema["properties"]
    expected = ["CLM-01", "CLM-02"]
    assert props["claims"]["items"]["properties"]["claim_id"]["enum"] == expected
    assert props["executive_summary_claim_ids"]["items"]["enum"] == expected
    assert props["sections"]["items"]["properties"]["claim_ids"]["items"]["enum"] == expected
    highlights = props["highlights"]["properties"]
    assert highlights["pros"]["items"]["enum"] == expected
    assert highlights["cons"]["items"]["enum"] == expected
    assert highlights["curriculum_alignment"]["items"]["properties"]["need_claim_ids"]["items"]["enum"] == expected
