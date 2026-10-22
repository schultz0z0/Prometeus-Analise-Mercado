"""Serviço de aplicação para planejamento de pesquisa, orçamento e chaves de cache (Etapa 05).

Gera o plano de pesquisa a partir da taxonomia do JEV, das features habilitadas no tenant
e das restrições de orçamento (ADR-0004).
"""

from __future__ import annotations

import hashlib
import uuid

from prometeus.domain.configuration import TenantConfig
from prometeus.domain.ports.market_sources import (
    KeywordSet,
    ResearchPlan,
    ResearchPlanStatus,
)


class ResearchPlanService:
    """Orquestra a criação e governança do plano de pesquisa e quotas de coleta."""

    DEFAULT_SOURCE_BUDGETS: dict[str, float] = {
        "google_trends": 0.00,
        "google_ads": 0.00,
        "youtube": 0.00,
        "apify_linkedin_jobs": 0.50,
        "apify_social_listening": 0.60,
        "apify_educational_offers": 0.40,
    }

    def generate_plan(
        self,
        analysis_id: str,
        tenant_config: TenantConfig,
        keyword_set: KeywordSet,
        taxonomy_area: str = "SEGUROS_E_RESSEGUROS",
        budget_limit_usd: float = 2.00,
    ) -> ResearchPlan:
        """Constrói o ResearchPlan determinístico com seleção de fontes e chave de cache."""
        enabled_sources: list[str] = ["google_trends"]

        # Condiciona fontes externas às features contratadas pelo tenant
        features = tenant_config.features

        if features.paid_competition:
            enabled_sources.append("google_ads")
            enabled_sources.append("apify_educational_offers")

        if features.social_listening:
            enabled_sources.append("youtube")
            enabled_sources.append("apify_social_listening")

        if features.job_market:
            enabled_sources.append("apify_linkedin_jobs")

        # Alocação de teto por fonte
        allocated: dict[str, float] = {
            src: self.DEFAULT_SOURCE_BUDGETS.get(src, 0.20) for src in enabled_sources
        }

        # Geração de cache key canônica determinística
        kw_hash = hashlib.sha256(
            ",".join(sorted(keyword_set.all_search_terms)).encode("utf-8")
        ).hexdigest()[:12]
        sources_hash = hashlib.sha256(
            ",".join(sorted(enabled_sources)).encode("utf-8")
        ).hexdigest()[:8]

        cache_key = f"{tenant_config.institution.id}:{taxonomy_area}:{kw_hash}:{sources_hash}"

        return ResearchPlan(
            id=str(uuid.uuid4()),
            analysis_id=analysis_id,
            tenant_id=tenant_config.institution.id,
            cache_key=cache_key,
            enabled_sources=enabled_sources,
            budget_limit_usd=budget_limit_usd,
            spent_usd=0.0,
            allocated_budget=allocated,
            status=ResearchPlanStatus.PLANNED,
        )
