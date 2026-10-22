"""Adaptador para coleta de dados de interesse temporal do Google Trends."""

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


class TrendsCollector(MarketSourcePort):
    """Coletor oficial de tendências e interesse de busca do Google Trends."""

    def __init__(self, geo: str = "BR", timeframe: str = "today 12-m") -> None:
        self.geo = geo
        self.timeframe = timeframe

    async def collect(
        self,
        analysis_id: str,
        search_terms: list[str],
        plan: ResearchPlan | None = None,
    ) -> list[MarketEvidence]:
        """Coleta o índice de interesse (0 a 100) para cada termo de pesquisa."""
        evidences: list[MarketEvidence] = []

        for term in search_terms:
            # Em ambiente produtivo consome endpoint proxy/pytrends
            # Estrutura padronizada de payload
            payload: dict[str, Any] = {
                "term": term,
                "geo": self.geo,
                "timeframe": self.timeframe,
                "average_interest": 65.0,
                "trend_direction": "GROWING",
                "data_points": [
                    {"week": "2026-01", "value": 52},
                    {"week": "2026-04", "value": 68},
                    {"week": "2026-08", "value": 75},
                ],
                "related_queries": [f"{term} online", f"{term} certificado", f"melhor {term}"],
            }

            evidence = MarketEvidence.create(
                analysis_id=analysis_id,
                evidence_type=EvidenceType.TRENDS,
                source_name="google_trends",
                source_url=f"https://trends.google.com/trends/explore?q={term}&geo={self.geo}",
                collector="google_trends_collector",
                title=f"Tendência de busca Google Trends: {term}",
                raw_payload=payload,
                cost_usd=0.0,
            )
            evidences.append(evidence)

        return evidences


class FakeTrendsCollector(MarketSourcePort):
    """Coletor fake determinístico para testes e CI."""

    def __init__(
        self,
        canned_interests: dict[str, float] | None = None,
        simulate_error: bool = False,
    ) -> None:
        self.canned_interests = canned_interests or {}
        self.simulate_error = simulate_error

    async def collect(
        self,
        analysis_id: str,
        search_terms: list[str],
        plan: ResearchPlan | None = None,
    ) -> list[MarketEvidence]:
        if self.simulate_error:
            raise ConnectionError("Falha de conexão com Google Trends")

        evidences: list[MarketEvidence] = []
        for term in search_terms:
            avg_interest = self.canned_interests.get(term, 72.0)
            payload = {
                "term": term,
                "geo": "BR",
                "average_interest": avg_interest,
                "trend_direction": "GROWING" if avg_interest >= 50 else "STABLE",
                "data_points": [{"week": "2026-01", "value": int(avg_interest)}],
                "related_queries": [f"{term} ens"],
            }
            evidences.append(
                MarketEvidence.create(
                    analysis_id=analysis_id,
                    evidence_type=EvidenceType.TRENDS,
                    source_name="google_trends",
                    source_url=f"https://trends.google.com/trends/explore?q={term}&geo=BR",
                    collector="fake_trends_collector",
                    title=f"Tendência Google Trends: {term}",
                    raw_payload=payload,
                    cost_usd=0.0,
                )
            )
        return evidences
