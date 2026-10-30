import pytest

from prometeus.application.evidence_features import EvidenceFeatureSet, VerifiedFeature
from prometeus.application.scoring_service import ScoringService


async def test_new_profile_separates_observed_score_from_coverage_and_contribution():
    service = ScoringService()
    result = await service.execute_scoring(
        profile_id="portfolio-v2",
        pillar_inputs={"paid_competition": {"is_present": True, "ad_count": 4}},
    )
    assert result.coverage_score == 0.2
    assert result.viability_score == 50
    assert result.partial_score == 50
    assert result.recommendation.value == "INSUFFICIENT_EVIDENCE"
    assert result.gate_details.model_dump()["weighted_contribution"] == 10


def test_ipd_and_actual_syllabus_confidence_are_used_in_v2_inputs():
    service = ScoringService()
    feature_set = EvidenceFeatureSet(
        {
            name: VerifiedFeature(name, value, ["source"], "test")
            for name, value in {
                "internal_ipd_score": 75,
                "internal_ipd_confidence": 0.65,
                "syllabus_fit_score": 80,
                "syllabus_confidence": 0.57,
                "syllabus_requires_review": 1,
                "reference_mean_price_brl": 15000,
                "pricing_confidence": 0.55,
            }.items()
        }
    )
    inputs = service.build_pillar_inputs(
        feature_set,
        profile_id="portfolio-v2",
        proposed_price_brl=19520,
        proposed_price_source_id="proposal",
    )
    assert inputs["internal_history"]["ipd_score"] == 75
    assert inputs["syllabus_fit"]["is_present"] is False
    assert inputs["syllabus_fit"]["confidence"] == 0.57
    assert inputs["pricing"]["market_median_price_brl"] == 15000


async def test_legacy_profile_aggregation_is_unchanged():
    result = await ScoringService().execute_scoring(
        pillar_inputs={"paid_competition": {"is_present": True, "ad_count": 4}}
    )
    assert result.viability_score == 10


@pytest.mark.parametrize("sufficient", [True, False])
async def test_pending_curriculum_review_cannot_become_approval(sufficient):
    service = ScoringService()
    values = {
        "internal_ipd_score": 95,
        "internal_ipd_confidence": 0.9,
        "ad_count": 8,
        "competition_index": 0.9,
        "monthly_search_volume": 5000,
        "average_interest": 90,
        "growth_trend_pct": 50,
        "open_jobs_count": 30,
        "salary_median_brl": 14000,
        "reference_mean_price_brl": 20000,
        "pricing_confidence": 0.8,
        "syllabus_fit_score": 90,
        "syllabus_confidence": 0.57,
        "syllabus_requires_review": 1,
    }
    if not sufficient:
        del values["internal_ipd_score"]
    inputs = service.build_pillar_inputs(
        EvidenceFeatureSet(
            {key: VerifiedFeature(key, value, ["source"], "test") for key, value in values.items()}
        ),
        profile_id="portfolio-v2",
        proposed_price_brl=20000,
        proposed_price_source_id="proposal",
    )
    result = await service.execute_scoring(inputs, profile_id="portfolio-v2")
    assert result.recommendation.value == (
        "REQUIRES_HUMAN_REVIEW" if sufficient else "INSUFFICIENT_EVIDENCE"
    )
    assert result.gate_details.passed_gates is False
    assert any("revisão" in reason.lower() for reason in result.gate_details.reasons)
