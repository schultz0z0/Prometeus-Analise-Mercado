from prometeus.application.evidence_features import EvidenceFeatureSet, VerifiedFeature
from prometeus.application.scoring_service import ScoringService
from prometeus.domain.analyses import AnalysisRecommendation


def observed(name: str, value: int | float, *evidence_ids: str) -> VerifiedFeature:
    return VerifiedFeature(
        name=name,
        value=value,
        evidence_ids=list(evidence_ids),
        method="integration_test_observation",
    )


def complete_features(*, market_strength: str) -> EvidenceFeatureSet:
    if market_strength == "high":
        market = {
            "ad_count": observed("ad_count", 8, "ad-high"),
            "competition_index": observed("competition_index", 0.8, "search-high"),
            "monthly_search_volume": observed("monthly_search_volume", 5000, "search-high"),
            "average_interest": observed("average_interest", 85, "trend-high"),
            "growth_trend_pct": observed("growth_trend_pct", 40, "trend-high"),
            "open_jobs_count": observed("open_jobs_count", 45, "jobs-high"),
            "market_median_price_brl": observed("market_median_price_brl", 15000, "offer-high"),
        }
    else:
        market = {
            "ad_count": observed("ad_count", 1, "ad-low"),
            "competition_index": observed("competition_index", 0.1, "search-low"),
            "monthly_search_volume": observed("monthly_search_volume", 50, "search-low"),
            "average_interest": observed("average_interest", 15, "trend-low"),
            "growth_trend_pct": observed("growth_trend_pct", -20, "trend-low"),
            "open_jobs_count": observed("open_jobs_count", 2, "jobs-low"),
            "market_median_price_brl": observed("market_median_price_brl", 15000, "offer-low"),
        }

    market.update(
        {
            "comparable_fit_score": observed("comparable_fit_score", 85, "ens-history"),
            "conversion_rate": observed("conversion_rate", 0.12, "ens-history"),
            "enrollments_count": observed("enrollments_count", 35, "ens-history"),
            "syllabus_fit_score": observed("syllabus_fit_score", 88, "decision-syllabus"),
            "market_pain_points_covered_pct": observed(
                "market_pain_points_covered_pct", 0.85, "decision-pains"
            ),
        }
    )
    return EvidenceFeatureSet(features=market)


def test_distinct_observed_collections_produce_distinct_scores_and_keep_provenance() -> None:
    service = ScoringService()
    high_inputs = service.build_pillar_inputs(
        complete_features(market_strength="high"),
        proposed_price_brl=14500,
        proposed_price_source_id="course-understanding-1",
    )
    low_inputs = service.build_pillar_inputs(
        complete_features(market_strength="low"),
        proposed_price_brl=14500,
        proposed_price_source_id="course-understanding-1",
    )

    profile = service.get_profile("default-v1")
    high = service.calculator.calculate_all(profile, high_inputs)
    low = service.calculator.calculate_all(profile, low_inputs)

    assert high[0] > low[0]
    assert high[4]["paid_competition"].features["evidence_ids"] == [
        "ad-high",
        "search-high",
    ]
    assert high[4]["pricing"].features["evidence_ids"] == [
        "course-understanding-1",
        "offer-high",
    ]


def test_missing_required_search_evidence_reduces_coverage_and_blocks_positive_result() -> None:
    service = ScoringService()
    features = complete_features(market_strength="high")
    features = EvidenceFeatureSet(
        features={
            name: feature
            for name, feature in features.features.items()
            if name not in {"monthly_search_volume", "average_interest", "growth_trend_pct"}
        }
    )
    inputs = service.build_pillar_inputs(
        features,
        proposed_price_brl=14500,
        proposed_price_source_id="course-understanding-1",
    )
    profile = service.get_profile("default-v1")
    viability, coverage, confidence, _, pillars = service.calculator.calculate_all(profile, inputs)
    gate = service.gate_evaluator.evaluate(
        viability_score=viability,
        coverage_score=coverage,
        confidence_score=confidence,
        pillar_scores=pillars,
        profile=profile,
    )

    assert pillars["search_and_media"].is_present is False
    assert coverage == 0.8
    assert gate.recommendation == AnalysisRecommendation.INSUFFICIENT_EVIDENCE
    assert any("search_and_media" in reason for reason in gate.reasons)
