"""Extração determinística de métricas observadas em evidências persistidas."""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from typing import Any

from prometeus.domain.ports.market_sources import EvidenceType, MarketEvidence


@dataclass(frozen=True)
class VerifiedFeature:
    name: str
    value: int | float
    evidence_ids: list[str]
    method: str


@dataclass(frozen=True)
class EvidenceFeatureSet:
    features: dict[str, VerifiedFeature]

    def get(self, name: str) -> VerifiedFeature | None:
        return self.features.get(name)

    def require(self, name: str) -> VerifiedFeature:
        feature = self.get(name)
        if feature is None:
            raise KeyError(f"Feature verificada ausente: {name}")
        return feature


_BRL_PRICE_RE = re.compile(r"(?:R\$|BRL)\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{1,2})?)", re.I)


def _positive_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float) and value >= 0:
        return float(value)
    return None


def _price_brl(payload: dict[str, Any]) -> float | None:
    for field_name in ("price_brl", "priceBrl", "tuition_brl"):
        value = _positive_number(payload.get(field_name))
        if value is not None and value > 0:
            return value
    raw = payload.get("price")
    if not isinstance(raw, str):
        return None
    match = _BRL_PRICE_RE.search(raw)
    if match is None:
        return None
    normalized = match.group(1).replace(".", "").replace(",", ".")
    try:
        value = float(normalized)
    except ValueError:
        return None
    return value if value > 0 else None


class EvidenceFeatureExtractor:
    """Não estima valores ausentes; apenas agrega campos observados e tipados."""

    @staticmethod
    def _observed_count(evidence: MarketEvidence) -> int:
        payload = evidence.sanitized_data
        nested_field = {
            EvidenceType.OFFER: "organicResults",
            EvidenceType.PAID_COMPETITION: "ads",
            EvidenceType.JOB_MARKET: "jobs",
            EvidenceType.SOCIAL_VOICE: "comments",
        }.get(evidence.evidence_type)
        if nested_field is not None and nested_field in payload:
            nested = payload.get(nested_field)
            return len(nested) if isinstance(nested, list) else 0
        return 1

    @staticmethod
    def _add_count_feature(
        features: dict[str, VerifiedFeature],
        *,
        name: str,
        evidences: list[MarketEvidence],
    ) -> None:
        counts = [
            (evidence, EvidenceFeatureExtractor._observed_count(evidence)) for evidence in evidences
        ]
        value = sum(count for _, count in counts)
        ids = [evidence.id for evidence, count in counts if count > 0]
        features[name] = VerifiedFeature(
            name=name,
            value=value,
            evidence_ids=ids,
            method="count_valid_items",
        )

    @staticmethod
    def _numeric_values(
        evidences: list[MarketEvidence], field_name: str
    ) -> list[tuple[str, float]]:
        values: list[tuple[str, float]] = []
        for evidence in evidences:
            value = _positive_number(evidence.sanitized_data.get(field_name))
            if value is not None:
                values.append((evidence.id, value))
        return values

    @staticmethod
    def _aggregate_numeric(
        features: dict[str, VerifiedFeature],
        *,
        name: str,
        values: list[tuple[str, float]],
        aggregation: str,
    ) -> None:
        if not values:
            return
        numbers = [value for _, value in values]
        if aggregation == "sum":
            aggregated = sum(numbers)
        elif aggregation == "median":
            aggregated = statistics.median(numbers)
        else:
            aggregated = statistics.fmean(numbers)
        if all(number.is_integer() for number in numbers) and aggregation == "sum":
            value: int | float = int(aggregated)
        else:
            value = round(aggregated, 4)
        features[name] = VerifiedFeature(
            name=name,
            value=value,
            evidence_ids=[evidence_id for evidence_id, _ in values],
            method=aggregation,
        )

    def extract(self, evidences: list[MarketEvidence]) -> EvidenceFeatureSet:
        by_type: dict[EvidenceType, list[MarketEvidence]] = {
            evidence_type: [] for evidence_type in EvidenceType
        }
        for evidence in evidences:
            by_type[evidence.evidence_type].append(evidence)

        features: dict[str, VerifiedFeature] = {}
        self._add_count_feature(
            features,
            name="ad_count",
            evidences=by_type[EvidenceType.PAID_COMPETITION],
        )
        self._add_count_feature(
            features,
            name="competitor_offer_count",
            evidences=by_type[EvidenceType.OFFER],
        )
        self._add_count_feature(
            features,
            name="open_jobs_count",
            evidences=by_type[EvidenceType.JOB_MARKET],
        )
        self._add_count_feature(
            features,
            name="social_mentions_count",
            evidences=by_type[EvidenceType.SOCIAL_VOICE],
        )

        prices = [
            (evidence.id, price)
            for evidence in by_type[EvidenceType.OFFER]
            if (price := _price_brl(evidence.sanitized_data)) is not None
        ]
        self._aggregate_numeric(
            features,
            name="market_median_price_brl",
            values=prices,
            aggregation="median",
        )

        search_evidence = by_type[EvidenceType.SEARCH_VOLUME]
        paid_evidence = by_type[EvidenceType.PAID_COMPETITION]
        job_evidence = by_type[EvidenceType.JOB_MARKET]
        trends_evidence = by_type[EvidenceType.TRENDS]
        for name, source, aggregation in (
            ("monthly_search_volume", search_evidence, "sum"),
            ("competition_index", search_evidence + paid_evidence, "mean"),
            ("cpc_brl", search_evidence + paid_evidence, "median"),
            ("salary_median_brl", job_evidence, "median"),
            ("average_interest", trends_evidence, "mean"),
            ("growth_trend_pct", trends_evidence, "mean"),
        ):
            self._aggregate_numeric(
                features,
                name=name,
                values=self._numeric_values(source, name),
                aggregation=aggregation,
            )

        return EvidenceFeatureSet(features=features)
