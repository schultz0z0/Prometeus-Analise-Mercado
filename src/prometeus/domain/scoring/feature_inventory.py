"""Inventário de features de scoring, alcançabilidade e dimensões de qualidade (Tarefa 4.1).

Rastreia cada feature observada:
feature -> normalizador/fonte -> disponibilidade -> dimensões de qualidade -> custo -> efeito em confiança/gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class QualityDimension(StrEnum):
    """Dimensões analíticas estritas de qualidade de evidência."""

    COMPLETENESS = "completeness"
    RELEVANCE = "relevance"
    RECENCY = "recency"
    DIVERSITY = "diversity"
    INFERENTIAL_STRENGTH = "inferential_strength"


@dataclass(frozen=True)
class FeatureInventoryItem:
    """Item do inventário de alcançabilidade de feature."""

    feature_name: str
    source_capability: str
    normalizer_name: str
    availability_condition: str
    target_pillar: str
    cost_usd: float
    quality_dimensions: dict[QualityDimension, float]
    effect_on_confidence: str
    effect_on_gates: list[str]


CANONICAL_FEATURE_INVENTORY: dict[str, FeatureInventoryItem] = {
    "market_median_price_brl": FeatureInventoryItem(
        feature_name="market_median_price_brl",
        source_capability="web_crawler",
        normalizer_name="OfferNormalizer",
        availability_condition="Página de concorrente com preço total ou parcelamento explícito observado",
        target_pillar="pricing",
        cost_usd=0.015,
        quality_dimensions={
            QualityDimension.COMPLETENESS: 0.90,
            QualityDimension.RELEVANCE: 0.95,
            QualityDimension.RECENCY: 0.85,
            QualityDimension.DIVERSITY: 0.80,
            QualityDimension.INFERENTIAL_STRENGTH: 0.90,
        },
        effect_on_confidence="Alimenta a confiança do pilar de preço com base na dispersão e número de concorrentes",
        effect_on_gates=["minimum_coverage", "minimum_confidence"],
    ),
    "paid_ad_count": FeatureInventoryItem(
        feature_name="paid_ad_count",
        source_capability="meta_ads_library",
        normalizer_name="AdNormalizer",
        availability_condition="Anúncios ativos de concorrentes com criativo educacional compatível",
        target_pillar="paid_competition",
        cost_usd=0.008,
        quality_dimensions={
            QualityDimension.COMPLETENESS: 0.85,
            QualityDimension.RELEVANCE: 0.80,
            QualityDimension.RECENCY: 0.95,
            QualityDimension.DIVERSITY: 0.75,
            QualityDimension.INFERENTIAL_STRENGTH: 0.70,
        },
        effect_on_confidence="Determina a saturação de mídia concorrente sem pressupor sucesso financeiro",
        effect_on_gates=["minimum_coverage"],
    ),
    "job_postings_count": FeatureInventoryItem(
        feature_name="job_postings_count",
        source_capability="linkedin_jobs",
        normalizer_name="JobNormalizer",
        availability_condition="Vagas de emprego com requisitos e competências profissionais explícitos",
        target_pillar="market_demand",
        cost_usd=0.012,
        quality_dimensions={
            QualityDimension.COMPLETENESS: 0.90,
            QualityDimension.RELEVANCE: 0.85,
            QualityDimension.RECENCY: 0.90,
            QualityDimension.DIVERSITY: 0.85,
            QualityDimension.INFERENTIAL_STRENGTH: 0.80,
        },
        effect_on_confidence="Sustenta empregabilidade e competências; não comprova demanda direta por curso",
        effect_on_gates=["minimum_coverage", "minimum_confidence"],
    ),
    "search_trend_average": FeatureInventoryItem(
        feature_name="search_trend_average",
        source_capability="google_trends",
        normalizer_name="TrendSeriesNormalizer",
        availability_condition="Série temporal contínua com pelo menos 8 pontos e hasData=True",
        target_pillar="search_interest",
        cost_usd=0.005,
        quality_dimensions={
            QualityDimension.COMPLETENESS: 0.95,
            QualityDimension.RELEVANCE: 0.80,
            QualityDimension.RECENCY: 0.95,
            QualityDimension.DIVERSITY: 0.70,
            QualityDimension.INFERENTIAL_STRENGTH: 0.75,
        },
        effect_on_confidence="Indica interesse relativo de busca; ausência de série não é procura zero",
        effect_on_gates=["minimum_coverage"],
    ),
    "internal_ipd_score": FeatureInventoryItem(
        feature_name="internal_ipd_score",
        source_capability="internal_history",
        normalizer_name="InternalHistoryService",
        availability_condition="Pelo menos 1 curso histórico da mesma família com similaridade temática >= 0.15",
        target_pillar="internal_history",
        cost_usd=0.0,
        quality_dimensions={
            QualityDimension.COMPLETENESS: 0.95,
            QualityDimension.RELEVANCE: 0.90,
            QualityDimension.RECENCY: 0.80,
            QualityDimension.DIVERSITY: 0.85,
            QualityDimension.INFERENTIAL_STRENGTH: 0.95,
        },
        effect_on_confidence="Reflete a similaridade média real dos comparáveis (mean_fit) e completude curricular",
        effect_on_gates=["minimum_coverage", "minimum_confidence"],
    ),
    "syllabus_fit_score": FeatureInventoryItem(
        feature_name="syllabus_fit_score",
        source_capability="syllabus_fit",
        normalizer_name="DecisionService",
        availability_condition="Grade da proposta auditada contra competências do mercado e diretrizes curriculares",
        target_pillar="syllabus_fit",
        cost_usd=0.002,
        quality_dimensions={
            QualityDimension.COMPLETENESS: 0.85,
            QualityDimension.RELEVANCE: 0.95,
            QualityDimension.RECENCY: 0.90,
            QualityDimension.DIVERSITY: 0.80,
            QualityDimension.INFERENTIAL_STRENGTH: 0.90,
        },
        effect_on_confidence="Julgamento formal de aderência; pendência de revisão humana impede aprovação comercial",
        effect_on_gates=["minimum_coverage", "minimum_confidence"],
    ),
}


def get_feature_inventory(feature_name: str) -> FeatureInventoryItem | None:
    return CANONICAL_FEATURE_INVENTORY.get(feature_name)

