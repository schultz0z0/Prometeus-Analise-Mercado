"""A01/A02: only verified content and explicit simulations reach presentation."""

from __future__ import annotations

import json
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from prometeus.application.economics_service import CourseEconomicsService
from prometeus.application.synthesize_dossier import DossierSynthesisService
from prometeus.domain.dossiers import DossierFactItem, DossierFacts, DossierOutput
from prometeus.domain.economics import CourseEconomicsInput


def presentation(proposal: dict):
    facts = DossierFacts(
        analysis_id="audit",
        course_name="Python para iniciantes",
        target_audience="Iniciantes",
        recommendation="INSUFFICIENT_EVIDENCE",
        viability_score=0,
        coverage_score=0,
        confidence_score=0,
    )
    dossier = DossierOutput(
        analysis_id=facts.analysis_id,
        executive_summary="Evidências insuficientes.",
        facts_hash=facts.compute_facts_hash(),
    )
    return DossierSynthesisService._build_visual_presentation_blocks(
        SimpleNamespace(course_name=facts.course_name, proposal_data=proposal),
        SimpleNamespace(viability_score=0, recommendation=facts.recommendation, confidence_score=0),
        facts,
        dossier,
    )


def explicit_inputs(**updates):
    inputs = {
        "total_price_brl": "2400.00",
        "installments": 1,
        "discount_rate_pct": "0",
        "default_and_refund_rate_pct": "0",
        "tax_rate_pct": "0",
        "instruction_and_coordination_cost_brl": "15000.00",
        "variable_cost_per_student_brl": "452.50",
        "marketing_campaign_cost_brl": "0",
        "cac_per_enrolled_brl": "0",
        "min_capacity": 10,
        "max_capacity": 30,
        "academic_duration_months": 1,
        "financial_duration_months": 1,
    }
    inputs.update(updates)
    return inputs


def test_missing_assumptions_do_not_create_financial_or_market_facts():
    result = presentation({})
    assert result["economics"]["status"] == "not_calculable"
    assert result["economics"]["scenarios"] == []
    assert result["economics"]["break_even_students"] is None
    assert result["personas"] == []
    assert result["curriculum_modules"] == []
    assert result["tactical_roadmap"] == []
    assert not any(result["swot"].values())
    assert "forte demanda" not in json.dumps(result, ensure_ascii=False).lower()
    assert "Preço Recomendado" not in json.dumps(result, ensure_ascii=False)
    assert result["contract_version"] == 2
    assert all("Benchmark" not in item.get("trend", "") for item in result["kpis"])


def test_market_reference_is_not_used_as_proposed_financial_price():
    result = presentation({"ticket": 100, "price_period": "monthly"})
    assert result["economics"]["status"] == "not_calculable"
    assert "total_price_brl" in result["economics"]["missing_inputs"]


def test_ecosystem_without_queries_does_not_claim_market_whitespace():
    result = presentation(
        {
            "_institution_context": {
                "competitors": [
                    {
                        "id": "x",
                        "name": "School X",
                        "category": "scale_ead",
                        "domains": ["example.edu"],
                    }
                ]
            }
        }
    )
    row = result["competitive_benchmark"]["rows"][0]
    assert row["status"] == "not_queried"
    assert "pioneirismo" not in json.dumps(result).lower()
    assert "corpo docente atuante" not in json.dumps(result).lower()


def benchmark_facts(*, calls=None, runs=None, items=None):
    proposal = {
        "_institution_context": {
            "competitors": [
                {
                    "id": "fgv",
                    "name": "FGV",
                    "domains": ["fgv.br"],
                    "category": "executive_business",
                }
            ]
        }
    }
    facts = DossierFacts(
        analysis_id="coverage",
        course_name="Governança de IA",
        target_audience="Gestores",
        recommendation="INSUFFICIENT_EVIDENCE",
        viability_score=0,
        coverage_score=0,
        confidence_score=0,
        items=items or [],
        research_plan={"tool_calls": calls or [], "tool_runs": runs or []},
    )
    return proposal, facts


def test_planned_fgv_query_skipped_by_budget_is_not_a_completed_search():
    from prometeus.application.ecosystem_presentation import build_ecosystem_presentation_blocks

    proposal, facts = benchmark_facts(
        calls=[
            {
                "id": "fgv-search",
                "capability": "google_search",
                "query": "site:fgv.br curso IA",
                "parameters": {"competitor_id": "fgv", "collection_phase": "discovery"},
            }
        ],
        runs=[
            {
                "id": "failed",
                "planned_call_id": "fgv-search",
                "status": "FAILED",
                "capability": "google_search",
                "parameters": {"observation_status": "budget_skipped"},
            }
        ],
    )
    block = build_ecosystem_presentation_blocks(proposal, facts, 24)["competitive_benchmark"]
    assert block["searched_total"] == 0
    assert block["coverage_complete"] is False
    assert block["rows"][0]["execution_status"] == "blocked"
    assert block["rows"][0]["status"] != "no_offer_observed"


def test_benchmark_keeps_multiple_offers_without_double_counting_institutions():
    from prometeus.application.ecosystem_presentation import build_ecosystem_presentation_blocks

    items = [
        DossierFactItem(
            evidence_id=f"offer-{i}",
            source_type="OFFER",
            title=f"Curso IA {i}",
            key_metrics={"matched_actor_id": "fgv", "actor_role": "configured_competitor"},
            summary="Oferta de curso confirmada",
            source_url=f"https://fgv.br/curso-{i}",
        )
        for i in (1, 2)
    ]
    proposal, facts = benchmark_facts(items=items)
    block = build_ecosystem_presentation_blocks(proposal, facts, 24)["competitive_benchmark"]
    assert block["offers_found_count"] == 1
    assert block["total_offers"] == 2
    assert len(block["rows"][0]["offers"]) == 2


def test_offer_accepted_for_another_purpose_does_not_become_a_direct_competitor():
    from prometeus.application.ecosystem_presentation import build_ecosystem_presentation_blocks

    proposal, facts = benchmark_facts(
        items=[
            DossierFactItem(
                evidence_id="news",
                source_type="OFFER",
                title="Notícia institucional de IA",
                key_metrics={"matched_actor_id": "fgv", "competition_relation": "not_qualified"},
                summary="Contexto curricular",
                source_url="https://fgv.br/noticias/ia",
            )
        ]
    )
    block = build_ecosystem_presentation_blocks(proposal, facts, 24)["competitive_benchmark"]
    assert block["total_offers"] == 0


def test_final_presentation_gate_rejects_visual_count_not_supported_by_facts():
    from prometeus.application.dossier_verifier import DossierVerifier

    proposal, facts = benchmark_facts()
    dossier = DossierOutput(
        analysis_id=facts.analysis_id,
        facts_hash=facts.compute_facts_hash(),
        executive_summary="Evidências insuficientes.",
    )
    blocks = DossierSynthesisService._build_visual_presentation_blocks(
        SimpleNamespace(proposal_data=proposal),
        None,
        facts,
        dossier,
    )
    blocks["competitive_benchmark"]["offers_found_count"] = 10
    issues = DossierVerifier().verify_presentation(dossier, facts, blocks, proposal)
    assert any(issue["code"] == "presentation_fact_mismatch" for issue in issues)


def test_fractional_cents_reconcile_and_discount_prose_uses_actual_rate():
    evaluation = CourseEconomicsService().evaluate(
        CourseEconomicsInput(
            **explicit_inputs(
                instruction_and_coordination_cost_brl="100.005",
                marketing_campaign_cost_brl="1.005",
                academic_duration_months=12,
                discount_rate_pct="98",
            )
        )
    )
    base = evaluation.scenarios["base"]
    assert (
        sum(month.projected_disbursements_brl for month in evaluation.monthly_cash_flow)
        == base.total_costs_brl
    )
    assert "103" not in " ".join(evaluation.scenarios["conservative"].assumptions)


def test_out_of_range_money_is_not_calculable_instead_of_crashing():
    result = presentation({"economics": explicit_inputs(total_price_brl="1e100")})
    assert result["economics"]["status"] == "not_calculable"


def test_flat_canonical_fields_and_nested_fields_have_the_same_result():
    assert (
        presentation(explicit_inputs())["economics"]["scenarios"]
        == presentation({"economics": explicit_inputs()})["economics"]["scenarios"]
    )


def test_negative_contribution_has_no_break_even_and_no_positive_scenario():
    result = presentation({"economics": explicit_inputs(total_price_brl="100")})
    economics = result["economics"]
    assert economics["status"] == "calculable"
    assert economics["break_even_students"] is None
    assert economics["is_margin_positive"] is False
    assert all(item["students"] <= 30 for item in economics["scenarios"])
    assert all(item["status"] == "warning" for item in economics["scenarios"])
    assert all(Decimal(item["net_profit"]) < 0 for item in economics["scenarios"])


def test_capacity_cannot_be_increased_to_make_a_scenario_profitable():
    result = presentation(
        {"economics": explicit_inputs(instruction_and_coordination_cost_brl="100000")}
    )
    economics = result["economics"]
    assert economics["break_even_students"] == 52
    assert economics["is_break_even_compatible_with_capacity"] is False
    assert all(item["students"] <= 30 for item in economics["scenarios"])
    assert all(Decimal(item["net_profit"]) < 0 for item in economics["scenarios"])
    assert economics["basis"] == "simulation_from_explicit_assumptions"
    assert economics["input_sources"]["total_price_brl"] == "proposal.economics.total_price_brl"


def test_partial_inputs_never_silently_use_default_tax_or_costs():
    result = presentation({"economics": {"total_price_brl": 2400}})
    assert result["economics"]["status"] == "not_calculable"
    assert "tax_rate_pct" in result["economics"]["missing_inputs"]
    assert "variable_cost_per_student_brl" in result["economics"]["missing_inputs"]


def test_capacity_contract_rejects_minimum_above_maximum():
    with pytest.raises(ValidationError, match="min_capacity"):
        CourseEconomicsInput(**explicit_inputs(min_capacity=31))


def test_monthly_cash_flow_reconciles_exactly_to_scenario():
    inputs = CourseEconomicsInput(
        **explicit_inputs(
            total_price_brl="2400.01",
            instruction_and_coordination_cost_brl="15000.01",
            academic_duration_months=7,
            financial_duration_months=3,
        )
    )
    evaluation = CourseEconomicsService().evaluate(inputs)
    base = evaluation.scenarios["base"]
    assert (
        sum(month.projected_receipts_brl for month in evaluation.monthly_cash_flow)
        == base.net_revenue_brl
    )
    assert (
        sum(month.projected_disbursements_brl for month in evaluation.monthly_cash_flow)
        == base.total_costs_brl
    )
    assert evaluation.monthly_cash_flow[-1].cumulative_cash_flow_brl == base.net_result_brl


def test_cent_allocation_never_creates_a_negative_last_payment():
    inputs = CourseEconomicsInput(
        **explicit_inputs(
            total_price_brl="0.30",
            instruction_and_coordination_cost_brl="0.30",
            variable_cost_per_student_brl="0",
            min_capacity=1,
            max_capacity=1,
            academic_duration_months=60,
            financial_duration_months=60,
        )
    )
    evaluation = CourseEconomicsService().evaluate(inputs)
    assert all(month.projected_receipts_brl >= 0 for month in evaluation.monthly_cash_flow)
    assert all(month.projected_disbursements_brl >= 0 for month in evaluation.monthly_cash_flow)
