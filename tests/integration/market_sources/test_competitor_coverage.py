"""Cobertura descreve execuções e ofertas sem inferir mercado a partir do plano."""

from importlib import import_module

COMPETITORS = [
    {"id": "fgv", "name": "FGV", "domains": ["fgv.br"]},
    {"id": "fiap", "name": "FIAP", "domains": ["fiap.com.br"]},
]


def coverage(calls=(), runs=(), offers=()):
    return import_module("prometeus.application.competitor_coverage").build_competitor_coverage(
        competitors=COMPETITORS, calls=list(calls), runs=list(runs), offers=list(offers)
    )


def call(identifier="fgv-search", phase="discovery", competitor_id="fgv"):
    return {
        "id": identifier,
        "capability": "google_search" if phase == "discovery" else "web_crawler",
        "parameters": {"competitor_id": competitor_id, "collection_phase": phase},
    }


def run(identifier="fgv-search", status="SUCCEEDED", count=0, **kwargs):
    return {
        "id": f"local-{identifier}",
        "planned_call_id": identifier,
        "provider_run_id": f"remote-{identifier}",
        "status": status,
        "valid_items_count": count,
        **kwargs,
    }


def test_planned_query_and_budget_skip_never_count_as_searched():
    result = coverage(
        [call()],
        [run(status="FAILED", provider_run_id=None, parameters={"observation_status": "budget_skipped"})],
    )
    assert result["searched_total"] == 0
    assert result["coverage_complete"] is False
    assert result["rows"][0]["execution_status"] == "blocked"
    assert result["rows"][0]["evidence_status"] == "not_observed"


def test_no_run_does_not_mean_no_offer():
    row = coverage([call()])["rows"][0]
    assert row["execution_status"] == "not_started"
    assert row["evidence_status"] == "not_observed"
    assert row["searched"] is False


def test_cluster_does_not_claim_each_institution_was_searched():
    clustered = {"id": "cluster", "parameters": {"competitor_ids": ["fgv", "fiap"]}}
    result = coverage([clustered], [run("cluster", count=10)])
    assert result["searched_total"] == 0
    assert result["coverage_complete"] is False


def test_completed_targeted_empty_search_counts_without_missing_crawler_urls():
    result = coverage(
        [call(), call("fgv-validation", "validation")],
        [run(status="EMPTY"), run("fgv-validation", "FAILED", provider_run_id=None)],
    )
    row = result["rows"][0]
    assert row["searched"] is True
    assert row["complete"] is True
    assert row["execution_status"] == "completed"
    assert row["evidence_status"] == "no_qualified_offer"


def test_positive_discovery_needs_page_validation():
    row = coverage([call(), call("fgv-validation", "validation")], [run(count=4)])["rows"][0]
    assert row["searched"] is True
    assert row["complete"] is False
    assert row["execution_status"] == "partial"
    assert row["evidence_status"] == "validation_pending"


def test_official_url_filter_can_finish_validation_without_buying_crawler():
    row = coverage(
        [call(), call("fgv-validation", "validation")],
        [run(count=3), run("fgv-validation", "EMPTY", provider_run_id=None,
            parameters={"observation_status": "no_candidates_to_validate"})],
    )["rows"][0]
    assert row["complete"] is True
    assert row["evidence_status"] == "no_qualified_offer"


def test_all_targeted_searches_and_validation_reconcile_complete_coverage():
    calls = [call(), call("fgv-validation", "validation"), call("fiap-search", competitor_id="fiap")]
    runs = [run(count=3), run("fgv-validation", count=2), run("fiap-search", "EMPTY")]
    result = coverage(calls, runs)
    assert result["configured_total"] == 2
    assert result["searched_total"] == 2
    assert result["completed_total"] == 2
    assert result["coverage_complete"] is True


def test_offers_do_not_hide_failed_validation_and_are_deduplicated_by_course_url():
    offer = {"competitor_id": "fgv", "evidence_id": "ev1", "source_url": "https://fgv.br/ia", "title": "Curso IA", "relation": "direct"}
    offers = [offer, {**offer, "evidence_id": "ev2", "source_url": "https://fgv.br/ia/"}, {**offer, "evidence_id": "ev3", "source_url": "https://fgv.br/lgpd", "title": "Curso LGPD"}]
    row = coverage(
        [call(), call("fgv-validation", "validation")],
        [run(count=3), run("fgv-validation", "FAILED", error_code="site_blocked")],
        offers,
    )["rows"][0]
    assert row["execution_status"] == "partial"
    assert row["evidence_status"] == "direct_offer"
    assert len(row["offers"]) == 2
    assert set(row["evidence_ids"]) == {"ev1", "ev2", "ev3"}
    assert row["failures"][0]["error_code"] == "site_blocked"


def test_followup_discovery_counts_by_explicit_competitor_identity():
    followup = call("followup-1", competitor_id="fiap")
    result = coverage([followup], [run("followup-1", "EMPTY")])
    assert result["rows"][1]["searched"] is True
    assert result["rows"][0]["searched"] is False


def test_pending_retry_and_uncertain_execution_remain_visible():
    result = coverage(
        [call(), call("fiap-search", competitor_id="fiap")],
        [run(status="RETRY_SCHEDULED", parameters={"attempt_count": 2}), run("fiap-search", "FAILED", parameters={"execution_status": "IN_DOUBT"})],
    )
    assert result["rows"][0]["execution_status"] == "retrying"
    assert result["rows"][1]["execution_status"] == "in_doubt"
    assert result["coverage_complete"] is False


def test_observed_offer_without_category_preserves_unknown_relation_in_benchmark():
    offer = {"competitor_id": "fgv", "evidence_id": "offer-unknown", "source_url": "https://fgv.br/curso-ia", "title": "Governança de IA", "relation": "unclassified"}
    row = coverage([call()], [run()], [offer])["rows"][0]
    assert row["evidence_status"] == "offer_relation_pending"
    assert row["offers"][0]["relation"] == "unclassified"
    assert row["searched"] is True


def test_verified_page_enriches_same_course_previously_observed_without_category_or_price():
    preliminary = {"competitor_id": "fgv", "evidence_id": "search", "source_url": "https://fgv.br/curso-ia", "title": "Curso IA", "relation": "unclassified", "price_display": "—", "workload_hours": "—"}
    page = {**preliminary, "evidence_id": "page", "relation": "adjacent", "relation_reason": "Categoria observada diferente", "price_display": "R$ 900", "workload_hours": "40h"}
    row = coverage([call()], [run()], [preliminary, page])["rows"][0]
    assert len(row["offers"]) == 1
    offer = row["offers"][0]
    assert offer["relation"] == "adjacent"
    assert offer["price_display"] == "R$ 900" and offer["workload_hours"] == "40h"
    assert offer["evidence_ids"] == ["search", "page"]


def test_tracking_parameters_do_not_duplicate_courses_but_course_ids_remain_distinct():
    base = {"competitor_id": "fgv", "title": "Curso IA", "relation": "adjacent"}
    offers = [
        {**base, "evidence_id": "search", "source_url": "https://fgv.br/curso?id=42&utm_source=google"},
        {**base, "evidence_id": "page", "source_url": "https://fgv.br/curso?srsltid=tracking&id=42"},
        {**base, "evidence_id": "different", "source_url": "https://fgv.br/curso?id=43"},
    ]
    result = coverage([call()], [run()], offers)
    assert result["total_offers"] == 2
    assert result["rows"][0]["offers"][0]["evidence_ids"] == ["search", "page"]


def test_mixed_crawler_success_keeps_offer_and_exposes_each_unresolved_page():
    offer = {"competitor_id": "fgv", "evidence_id": "offer-1", "source_url": "https://fgv.br/ia", "title": "Curso IA", "relation": "direct"}
    result = coverage(
        [call(), call("fgv-validation", "validation"), call("fiap-search", competitor_id="fiap")],
        [run(count=3), run("fgv-validation", count=1, parameters={
            "observation_status": "observed",
            "url_outcomes": {
                "https://fgv.br/ia": "fetched",
                "https://fgv.br/lgpd": "blocked",
                "https://fgv.br/governanca": "extraction_failed",
            },
        }), run("fiap-search", "EMPTY")],
        [offer],
    )
    row = result["rows"][0]
    assert row["searched"] is True
    assert row["complete"] is False
    assert row["execution_status"] == "partial"
    assert row["evidence_status"] == "direct_offer"
    assert row["offers"][0]["evidence_ids"] == ["offer-1"]
    assert {(failure["source_url"], failure["error_code"]) for failure in row["failures"]} == {
        ("https://fgv.br/lgpd", "blocked"),
        ("https://fgv.br/governanca", "extraction_failed"),
    }
    assert result["completed_total"] == 1
    assert result["coverage_complete"] is False


def test_recovered_url_outcomes_clear_the_operational_gap():
    row = coverage(
        [call(), call("fgv-validation", "validation")],
        [run(count=2), run("fgv-validation", count=2, parameters={
            "observation_status": "observed",
            "url_outcomes": {"https://fgv.br/ia": "fetched", "https://fgv.br/lgpd": "fetched"},
        })],
    )["rows"][0]
    assert row["execution_status"] == "completed"
    assert row["complete"] is True
    assert row["failures"] == []
