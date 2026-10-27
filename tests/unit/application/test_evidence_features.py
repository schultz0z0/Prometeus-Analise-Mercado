from prometeus.application.evidence_features import EvidenceFeatureExtractor
from prometeus.domain.ports.market_sources import EvidenceType, MarketEvidence


def evidence(
    evidence_id: str,
    evidence_type: EvidenceType,
    payload: dict[str, object],
) -> MarketEvidence:
    return MarketEvidence.create(
        evidence_id=evidence_id,
        analysis_id="analysis-features",
        evidence_type=evidence_type,
        source_name=f"source-{evidence_id}",
        source_url=f"https://example.com/{evidence_id}",
        collector="contract-test",
        title=evidence_id,
        raw_payload=payload,
        sanitized_data=payload,
    )


def test_extracts_only_observed_market_features_with_evidence_ids() -> None:
    evidences = [
        evidence("ad-1", EvidenceType.PAID_COMPETITION, {"id": "ad-1"}),
        evidence(
            "offer-1",
            EvidenceType.OFFER,
            {"title": "MBA A", "price": "R$ 720,00"},
        ),
        evidence(
            "offer-2",
            EvidenceType.OFFER,
            {"title": "MBA B", "price_brl": 1250.0},
        ),
        evidence("job-1", EvidenceType.JOB_MARKET, {"title": "Analista"}),
        evidence("job-2", EvidenceType.JOB_MARKET, {"title": "Especialista"}),
        evidence("social-1", EvidenceType.SOCIAL_VOICE, {"text": "curso de seguros"}),
        evidence(
            "trends-1",
            EvidenceType.TRENDS,
            {"average_interest": 64.0, "growth_trend_pct": 12.5},
        ),
        evidence(
            "volume-1",
            EvidenceType.SEARCH_VOLUME,
            {"monthly_search_volume": 2300, "competition_index": 0.71, "cpc_brl": 4.2},
        ),
    ]

    result = EvidenceFeatureExtractor().extract(evidences)

    assert result.require("ad_count").value == 1
    assert result.require("ad_count").evidence_ids == ["ad-1"]
    assert result.require("competitor_offer_count").value == 2
    assert result.require("open_jobs_count").value == 2
    assert result.require("social_mentions_count").value == 1
    assert result.require("market_median_price_brl").value == 985.0
    assert result.require("market_median_price_brl").evidence_ids == ["offer-1", "offer-2"]
    assert result.require("average_interest").value == 64.0
    assert result.require("growth_trend_pct").value == 12.5
    assert result.require("monthly_search_volume").value == 2300
    assert result.require("competition_index").value == 0.71
    assert result.require("cpc_brl").value == 4.2


def test_absent_metric_stays_absent_instead_of_receiving_a_default() -> None:
    result = EvidenceFeatureExtractor().extract(
        [
            evidence(
                "google-page",
                EvidenceType.OFFER,
                {"searchQuery": {"term": "curso seguros"}, "organicResults": []},
            )
        ]
    )

    assert result.get("monthly_search_volume") is None
    assert result.get("competition_index") is None
    assert result.get("cpc_brl") is None
    assert result.get("average_interest") is None
    assert result.require("competitor_offer_count").value == 0


def test_invalid_or_untrusted_price_strings_are_not_coerced_into_market_prices() -> None:
    result = EvidenceFeatureExtractor().extract(
        [
            evidence("valid", EvidenceType.OFFER, {"price": "R$ 1.299,90"}),
            evidence("invalid", EvidenceType.OFFER, {"price": "a partir de consulte-nos"}),
            evidence("negative", EvidenceType.OFFER, {"price_brl": -100}),
        ]
    )

    price = result.require("market_median_price_brl")
    assert price.value == 1299.9
    assert price.evidence_ids == ["valid"]
