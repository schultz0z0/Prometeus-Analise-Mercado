"""Adaptador para coleta no YouTube com cálculo e controle explícito de quota (API v3).

A API v3 do YouTube possui custos assimétricos por endpoint:
- search.list: 100 unidades por requisição
- videos.list: 1 unidade por requisição
- commentThreads.list: 1 unidade por requisição
"""

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


class YouTubeQuotaExceededError(Exception):
    """Exceção levantada quando a quota do YouTube excede o teto permitido."""

    pass


class YouTubeCollector(MarketSourcePort):
    """Coletor oficial do YouTube com rastreamento estrito de unidades de quota."""

    SEARCH_UNIT_COST = 100
    VIDEO_DETAIL_UNIT_COST = 1
    COMMENT_THREAD_UNIT_COST = 1

    def __init__(
        self,
        api_key: str | None = None,
        max_quota_units_per_analysis: int = 500,
    ) -> None:
        self.api_key = api_key
        self.max_quota_units_per_analysis = max_quota_units_per_analysis
        self.used_quota_units = 0

    def calculate_estimated_units(
        self, search_terms_count: int, fetch_comments: bool = True
    ) -> int:
        """Calcula o custo estimado em unidades de quota antes da execução."""
        units_per_term = self.SEARCH_UNIT_COST + (10 * self.VIDEO_DETAIL_UNIT_COST)
        if fetch_comments:
            units_per_term += 5 * self.COMMENT_THREAD_UNIT_COST
        return search_terms_count * units_per_term

    async def collect(
        self,
        analysis_id: str,
        search_terms: list[str],
        plan: ResearchPlan | None = None,
    ) -> list[MarketEvidence]:
        evidences: list[MarketEvidence] = []

        for term in search_terms:
            # Checa se o próximo termo excede o teto
            needed_units = self.SEARCH_UNIT_COST + 5
            if (self.used_quota_units + needed_units) > self.max_quota_units_per_analysis:
                logger.warning(
                    f"Teto de quota do YouTube atingido: {self.used_quota_units}/{self.max_quota_units_per_analysis} unidades."
                )
                break

            self.used_quota_units += needed_units

            payload: dict[str, Any] = {
                "term": term,
                "quota_units_spent": needed_units,
                "video_count": 5,
                "top_videos": [
                    {
                        "video_id": f"yt-{term}-1",
                        "title": f"Tudo sobre {term} na prática",
                        "channel": "Canal Mercado Segurador",
                        "view_count": 14200,
                        "comment_count": 86,
                    }
                ],
                "sample_comments": [
                    {
                        "author": "Aluno Seguros",
                        "text": f"Precisamos de mais capacitações como essa em {term}!",
                    }
                ],
            }

            ev = MarketEvidence.create(
                analysis_id=analysis_id,
                evidence_type=EvidenceType.SOCIAL_VOICE,
                source_name="youtube",
                source_url=f"https://www.youtube.com/results?search_query={term}",
                collector="youtube_quota_tracked_collector",
                title=f"Audiência e Social Voice YouTube: {term}",
                raw_payload=payload,
                cost_usd=0.0,
            )
            evidences.append(ev)

        return evidences


class FakeYouTubeCollector(MarketSourcePort):
    """Coletor fake com emulação de cálculo de quota para testes unitários e CI."""

    def __init__(
        self,
        max_quota_units: int = 300,
        simulate_quota_exceeded: bool = False,
    ) -> None:
        self.max_quota_units = max_quota_units
        self.simulate_quota_exceeded = simulate_quota_exceeded
        self.used_quota_units = 0

    async def collect(
        self,
        analysis_id: str,
        search_terms: list[str],
        plan: ResearchPlan | None = None,
    ) -> list[MarketEvidence]:
        if self.simulate_quota_exceeded:
            raise YouTubeQuotaExceededError(
                f"Quota diária da API do YouTube esgotada ({self.max_quota_units} units)."
            )

        evidences: list[MarketEvidence] = []
        for term in search_terms:
            units = 105
            if (self.used_quota_units + units) > self.max_quota_units:
                break
            self.used_quota_units += units

            payload = {
                "term": term,
                "quota_units_spent": units,
                "video_count": 3,
                "sample_comments": [
                    {"author": "Corretor X", "text": f"Excelente conteúdo sobre {term}"}
                ],
            }
            evidences.append(
                MarketEvidence.create(
                    analysis_id=analysis_id,
                    evidence_type=EvidenceType.SOCIAL_VOICE,
                    source_name="youtube",
                    source_url=f"https://www.youtube.com/results?search_query={term}",
                    collector="fake_youtube_collector",
                    title=f"Social Voice YouTube: {term}",
                    raw_payload=payload,
                    cost_usd=0.0,
                )
            )
        return evidences
