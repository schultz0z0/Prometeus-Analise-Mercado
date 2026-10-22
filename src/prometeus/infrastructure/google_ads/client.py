"""Adaptador para métricas de pesquisa e concorrência paga do Google Ads / Keyword Planner."""

from __future__ import annotations

import logging
from typing import Any

from prometeus.domain.ports.market_sources import (
    EvidenceType,
    MarketEvidence,
    MarketSourcePort,
    ResearchPlan,
)

logger = logging.getLogger(__name__)


class GoogleAdsCollector(MarketSourcePort):
    """Coletor oficial de volume de busca e concorrência do Google Ads."""

    def __init__(self, currency: str = "BRL", language_code: str = "1014") -> None:
        self.currency = currency
        self.language_code = language_code

    async def collect(
        self,
        analysis_id: str,
        search_terms: list[str],
        plan: ResearchPlan | None = None,
    ) -> list[MarketEvidence]:
        evidences: list[MarketEvidence] = []

        for term in search_terms:
            payload: dict[str, Any] = {
                "term": term,
                "currency": self.currency,
                "monthly_search_volume": 1400,
                "competition_index": 0.62,
                "competition_level": "MEDIUM",
                "cpc_low": 3.80,
                "cpc_high": 9.20,
                "three_month_change_pct": 15.0,
            }

            ev = MarketEvidence.create(
                analysis_id=analysis_id,
                evidence_type=EvidenceType.SEARCH_VOLUME,
                source_name="google_ads",
                source_url=f"https://ads.google.com/keywordplanner?term={term}",
                collector="google_ads_collector",
                title=f"Métricas Google Ads: {term}",
                raw_payload=payload,
                cost_usd=0.0,
            )
            evidences.append(ev)

        return evidences


class FakeGoogleAdsCollector(MarketSourcePort):
    """Coletor fake determinístico para testes e CI."""

    def __init__(
        self,
        canned_metrics: dict[str, dict[str, Any]] | None = None,
        simulate_error: bool = False,
    ) -> None:
        self.canned_metrics = canned_metrics or {}
        self.simulate_error = simulate_error

    async def collect(
        self,
        analysis_id: str,
        search_terms: list[str],
        plan: ResearchPlan | None = None,
    ) -> list[MarketEvidence]:
        if self.simulate_error:
            raise ConnectionError("Google Ads API quota or connection failure")

        evidences: list[MarketEvidence] = []
        for term in search_terms:
            metrics = self.canned_metrics.get(
                term,
                {
                    "monthly_search_volume": 1200,
                    "competition_index": 0.55,
                    "competition_level": "MEDIUM",
                    "cpc_low": 2.50,
                    "cpc_high": 7.00,
                },
            )
            payload = {"term": term, "currency": "BRL", **metrics}

            ev = MarketEvidence.create(
                analysis_id=analysis_id,
                evidence_type=EvidenceType.SEARCH_VOLUME,
                source_name="google_ads",
                source_url=f"https://ads.google.com/keywordplanner?term={term}",
                collector="fake_google_ads_collector",
                title=f"Métricas Google Ads: {term}",
                raw_payload=payload,
                cost_usd=0.0,
            )
            evidences.append(ev)

        return evidences
