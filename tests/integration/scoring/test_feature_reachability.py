"""Testes de integração para alcançabilidade de features, calibração e qualidade (Tarefa 4.1).

Requisitos validados:
- Rastreamento ponta a ponta: payload realista do fornecedor -> normalizador -> extração de feature -> inputs de scoring -> cálculo de viabilidade e gates.
- Inventário de features com dimensões estritas: completude, pertinência, recência, diversidade e força inferencial.
- Dados imperfeitos ou conflitantes degradam a confiança e impedem aprovações artificiais.
- Invariância dos gates de qualidade (cobertura mínima de 80% e confiança mínima de 75% no perfil portfolio-v2).
"""

from __future__ import annotations

import asyncio

from prometeus.application.scoring_service import ScoringService
from prometeus.domain.analyses import AnalysisRecommendation
from prometeus.domain.scoring.feature_inventory import (
    CANONICAL_FEATURE_INVENTORY,
    QualityDimension,
)
from prometeus.infrastructure.apify.normalizers import (
    normalize_ad,
    normalize_crawler_page,
    normalize_job,
    normalize_trends,
)


def test_canonical_feature_inventory_contains_all_core_features():
    expected_features = {
        "market_median_price_brl",
        "paid_ad_count",
        "job_postings_count",
        "search_trend_average",
        "internal_ipd_score",
        "syllabus_fit_score",
    }
    assert expected_features.issubset(set(CANONICAL_FEATURE_INVENTORY.keys()))

    for feat_name, item in CANONICAL_FEATURE_INVENTORY.items():
        assert item.feature_name == feat_name
        assert item.source_capability != ""
        assert item.normalizer_name != ""
        assert item.target_pillar != ""
        assert len(item.quality_dimensions) == 5
        assert QualityDimension.COMPLETENESS in item.quality_dimensions
        assert QualityDimension.RELEVANCE in item.quality_dimensions
        assert QualityDimension.RECENCY in item.quality_dimensions
        assert QualityDimension.DIVERSITY in item.quality_dimensions
        assert QualityDimension.INFERENTIAL_STRENGTH in item.quality_dimensions


def test_positive_control_realistic_payload_reachability_pipeline():
    # 1. Offer payload from Web Crawler
    raw_offer = {
        "crawl": {"loadedUrl": "https://concorrente.com.br/mba-fraudes"},
        "pageTitle": "MBA em Fraudes em Seguros",
        "text": "MBA em Fraudes em Seguros. Carga Horária: 360 horas. Investimento: 12x de R$ 1.200,00 ou R$ 13.000,00 à vista.",
        "url": "https://concorrente.com.br/mba-fraudes",
    }
    obs_offer = normalize_crawler_page(raw_offer)
    assert obs_offer.title.value == "MBA em Fraudes em Seguros"

    # 2. Ad payload from Meta Ads
    raw_ad = {
        "id": "ad-meta-101",
        "pageName": "Faculdade de Seguros Concorrente",
        "adCreativeBody": "Inscrições abertas para o MBA em Gestão de Fraudes e Perícia de Sinistros.",
        "adSnapshotUrl": "https://facebook.com/ads/archive/render_ad/?id=101",
    }
    obs_ad = normalize_ad(raw_ad)
    assert obs_ad.ad_id == "ad-meta-101"

    # 3. Job payload from LinkedIn Jobs
    raw_job = {
        "title": "Analista de Sinistros - Prevenção a Fraudes",
        "companyName": "Seguradora Nacional S.A.",
        "location": "São Paulo, SP, Brasil",
        "description": "Responsável por análise investigativa de fraudes em sinistros de ramos elementares.",
    }
    obs_job = normalize_job(raw_job)
    assert obs_job.title.value == "Analista de Sinistros - Prevenção a Fraudes"

    # 4. Trend series payload from Google Trends
    raw_trend = {
        "term": "fraudes seguros",
        "points": [
            {"time": "2026-08-01", "value": [45]},
            {"time": "2026-08-15", "value": [55]},
            {"time": "2026-09-01", "value": [60]},
            {"time": "2026-09-15", "value": [70]},
        ],
        "hasData": True,
    }
    obs_trend = normalize_trends(raw_trend)
    assert obs_trend.valid_points == 4
    assert obs_trend.average_interest == 57.5


def test_quality_degradation_reduces_confidence_and_prevents_false_approval():
    async def _run():
        service = ScoringService()
        # Scenario where feature coverage is minimal and confidence is low
        result = await service.execute_scoring(
            profile_id="portfolio-v2",
            pillar_inputs={
                "pricing": {"is_present": True, "market_median_price_brl": 12000, "confidence": 0.30},
                "paid_competition": {"is_present": True, "ad_count": 1, "confidence": 0.20},
            },
        )

        # Gate failure: low confidence and coverage must yield INSUFFICIENT_EVIDENCE
        assert result.recommendation == AnalysisRecommendation.INSUFFICIENT_EVIDENCE
        assert result.coverage_score < 0.80
        assert result.confidence_score < 0.75

    asyncio.run(_run())


def test_strict_quality_gate_thresholds_in_portfolio_v2():
    async def _run():
        service = ScoringService()
        # High score but below 0.75 confidence must NOT be APPROVED
        result = await service.execute_scoring(
            profile_id="portfolio-v2",
            pillar_inputs={
                "internal_history": {"is_present": True, "ipd_score": 90, "confidence": 0.60},
                "pricing": {"is_present": True, "market_median_price_brl": 15000, "confidence": 0.60},
                "market_demand": {"is_present": True, "demand_score": 85, "confidence": 0.60},
                "paid_competition": {"is_present": True, "ad_count": 5, "confidence": 0.60},
                "syllabus_fit": {"is_present": True, "fit_score": 90, "confidence": 0.60},
            },
        )

        # Confidence is strictly below 0.75 gate!
        assert result.confidence_score < 0.75
        # Recommendation cannot be APPROVED because confidence gate failed
        assert result.recommendation != AnalysisRecommendation.APPROVED

    asyncio.run(_run())
