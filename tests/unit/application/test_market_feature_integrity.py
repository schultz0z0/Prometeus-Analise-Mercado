import pytest

from prometeus.application.evidence_features import EvidenceFeatureExtractor
from prometeus.application.scoring_service import ScoringService
from prometeus.domain.ports.market_sources import EvidenceType, MarketEvidence


def item(kind: EvidenceType, data: dict, name: str = "item") -> MarketEvidence:
    return MarketEvidence.create(
        analysis_id="audit",
        evidence_type=kind,
        source_name="apify_test",
        source_url=f"https://example.edu/{name}",
        collector="test",
        title=name,
        raw_payload=data,
        sanitized_data=data,
        evidence_id=name,
    )


def test_no_collection_does_not_create_zero_count_features_or_present_pillars():
    features = EvidenceFeatureExtractor().extract([])
    inputs = ScoringService().build_pillar_inputs(features)
    assert features.get("open_jobs_count") is None
    assert features.get("ad_count") is None
    assert not inputs["employability"]["is_present"]
    assert not inputs["paid_competition"]["is_present"]


def test_observed_empty_result_keeps_its_query_provenance():
    features = EvidenceFeatureExtractor().extract([item(EvidenceType.JOB_MARKET, {"jobs": []})])
    count = features.require("open_jobs_count")
    assert count.value == 0
    assert count.evidence_ids == ["item"]


def test_rejected_semantic_evidence_does_not_contribute_to_counts():
    features = EvidenceFeatureExtractor().extract(
        [item(EvidenceType.PAID_COMPETITION, {"id": "ad", "_qualification": {"accepted": False}})]
    )
    assert features.get("ad_count") is None


def test_brazilian_job_sample_excludes_foreign_and_unknown_locations():
    features = EvidenceFeatureExtractor(geography="Brasil").extract(
        [
            item(EvidenceType.JOB_MARKET, {"title": "Advogado", "location": "Irving, TX"}, "us"),
            item(
                EvidenceType.JOB_MARKET,
                {"title": "Advogado", "location": "São Paulo, SP, Brazil"},
                "br",
            ),
            item(EvidenceType.JOB_MARKET, {"title": "Advogado"}, "unknown"),
        ]
    )
    count = features.require("open_jobs_count")
    assert count.value == 1
    assert count.evidence_ids == ["br"]


def test_brazil_scope_with_delivery_note_keeps_brazil_jobs_and_excludes_foreign():
    extractor = EvidenceFeatureExtractor(
        geography="Brasil; participação online de qualquer localidade"
    )
    features = extractor.extract(
        [
            item(
                EvidenceType.JOB_MARKET,
                {"title": "Gerente de Sinistros", "location": "São Paulo, São Paulo, Brazil"},
                "br",
            ),
            item(EvidenceType.JOB_MARKET, {"title": "Gerente", "location": "Irving, TX"}, "us"),
            item(EvidenceType.JOB_MARKET, {"title": "Gerente"}, "unknown"),
        ]
    )
    assert features.require("open_jobs_count").value == 1
    assert features.require("open_jobs_count").evidence_ids == ["br"]


def test_trends_series_is_normalized_without_fabricating_missing_points():
    features = EvidenceFeatureExtractor().extract(
        [
            item(
                EvidenceType.TRENDS,
                {
                    "interestOverTime_timelineData": [
                        {"time": "1", "value": [10], "hasData": [True]},
                        {"time": "2", "value": [20], "hasData": [True]},
                        {"time": "3", "value": [30], "hasData": [True]},
                        {"time": "4", "value": [40], "hasData": [True]},
                        {"time": "5", "value": [0], "hasData": [False]},
                        {"time": "6", "value": [100], "isPartial": True},
                    ]
                },
            )
        ]
    )
    assert features.require("average_interest").value == 25
    assert features.require("growth_trend_pct").value == pytest.approx(133.3333)


def test_incompatible_price_periods_are_not_pooled():
    features = EvidenceFeatureExtractor(price_period="total").extract(
        [
            item(EvidenceType.OFFER, {"price_brl": 900, "price_period": "monthly"}, "monthly"),
            item(EvidenceType.OFFER, {"price_brl": 12000, "price_period": "total"}, "total"),
            item(EvidenceType.OFFER, {"price_brl": 800}, "unspecified"),
        ]
    )
    assert features.require("market_median_price_brl").value == 12000
    assert features.require("market_median_price_brl").evidence_ids == ["total"]


def test_pillar_with_a_value_but_no_provenance_is_absent():
    from prometeus.application.evidence_features import EvidenceFeatureSet, VerifiedFeature

    features = EvidenceFeatureSet(
        features={"open_jobs_count": VerifiedFeature("open_jobs_count", 10, [], "test")}
    )
    assert not ScoringService().build_pillar_inputs(features)["employability"]["is_present"]


def test_full_price_without_thousands_separator_and_published_period():
    features = EvidenceFeatureExtractor(price_period="total").extract(
        [item(EvidenceType.OFFER, {"text": "Investimento total R$ 12000,00 à vista"})]
    )
    assert features.require("market_median_price_brl").value == 12000


def test_declining_trend_is_an_observed_negative_value():
    features = EvidenceFeatureExtractor().extract(
        [item(EvidenceType.TRENDS, {"average_interest": 20, "growth_trend_pct": -25})]
    )
    assert features.require("growth_trend_pct").value == -25


def test_repeated_offer_urls_do_not_bias_price_median_and_keep_all_provenance():
    from dataclasses import replace

    first = item(EvidenceType.OFFER, {"price_brl": 900}, "first")
    repeated = replace(
        item(EvidenceType.OFFER, {"price_brl": 900, "_discovery": {"query": "other"}}, "repeat"),
        source_url=first.source_url + "?utm_source=search",
    )
    second = item(EvidenceType.OFFER, {"price_brl": 1800}, "second")
    features = EvidenceFeatureExtractor().extract([first, repeated, second])
    assert features.require("market_median_price_brl").value == 1350
    assert features.require("competitor_offer_count").value == 2
    assert set(features.require("market_median_price_brl").evidence_ids) == {
        "first",
        "repeat",
        "second",
    }


def test_registration_fee_is_not_used_as_monthly_tuition():
    features = EvidenceFeatureExtractor(price_period="monthly").extract(
        [item(EvidenceType.OFFER, {"text": "Taxa de matrícula R$ 100. Mensalidade R$ 900."})]
    )
    assert features.get("market_median_price_brl") is None
