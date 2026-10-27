"""Testes de contrato para os coletores de fontes externas (Trends, Ads, YouTube, Apify)."""

import pytest

from prometeus.domain.configuration import AppSettings
from prometeus.domain.ports.market_sources import (
    EvidenceType,
    ResearchPlan,
)
from prometeus.infrastructure.apify.client import (
    FakeApifyCollector,
)
from prometeus.infrastructure.apify.registry import ApifyActorRegistry
from prometeus.infrastructure.google_ads.client import (
    FakeGoogleAdsCollector,
    GoogleAdsCollector,
)
from prometeus.infrastructure.trends.client import (
    FakeTrendsCollector,
    TrendsCollector,
)
from prometeus.infrastructure.youtube.client import (
    FakeYouTubeCollector,
    YouTubeCollector,
    YouTubeQuotaExceededError,
)


@pytest.fixture
def sample_plan() -> ResearchPlan:
    return ResearchPlan(
        analysis_id="an-123",
        tenant_id="ens",
        cache_key="ens:seguros:key1",
        budget_limit_usd=1.00,
    )


# --- Google Trends ---


@pytest.mark.asyncio
async def test_trends_collector_structure() -> None:
    collector = TrendsCollector(geo="BR")
    evidences = await collector.collect(
        analysis_id="an-123",
        search_terms=["seguro auto", "perícia de sinistros"],
    )

    assert len(evidences) == 2
    ev = evidences[0]
    assert ev.evidence_type == EvidenceType.TRENDS
    assert ev.source_name == "google_trends"
    assert "average_interest" in ev.raw_payload
    assert ev.cost_usd == 0.0


@pytest.mark.asyncio
async def test_fake_trends_collector_custom_interest() -> None:
    collector = FakeTrendsCollector(canned_interests={"subscrição": 85.0})
    evidences = await collector.collect(analysis_id="an-123", search_terms=["subscrição"])

    assert len(evidences) == 1
    assert evidences[0].raw_payload["average_interest"] == 85.0
    assert evidences[0].raw_payload["trend_direction"] == "GROWING"


# --- Google Ads ---


@pytest.mark.asyncio
async def test_google_ads_collector_structure() -> None:
    collector = GoogleAdsCollector()
    evidences = await collector.collect(
        analysis_id="an-123",
        search_terms=["mba seguros ens"],
    )

    assert len(evidences) == 1
    ev = evidences[0]
    assert ev.evidence_type == EvidenceType.SEARCH_VOLUME
    assert ev.source_name == "google_ads"
    assert ev.raw_payload["monthly_search_volume"] > 0
    assert ev.raw_payload["cpc_low"] > 0


@pytest.mark.asyncio
async def test_fake_google_ads_collector() -> None:
    collector = FakeGoogleAdsCollector(
        canned_metrics={"curso sinistro": {"monthly_search_volume": 2400, "competition_index": 0.8}}
    )
    evidences = await collector.collect(analysis_id="an-123", search_terms=["curso sinistro"])

    assert evidences[0].raw_payload["monthly_search_volume"] == 2400
    assert evidences[0].raw_payload["competition_index"] == 0.8


# --- YouTube com Quota Control ---


@pytest.mark.asyncio
async def test_youtube_collector_quota_calculation() -> None:
    collector = YouTubeCollector(max_quota_units_per_analysis=250)
    estimated = collector.calculate_estimated_units(search_terms_count=2, fetch_comments=True)
    # (100 + 10*1 + 5*1) * 2 = 115 * 2 = 230
    assert estimated == 230

    evidences = await collector.collect(
        analysis_id="an-123",
        search_terms=["curso resseguro", "pericia engenharia"],
    )
    assert len(evidences) == 2
    assert collector.used_quota_units == 210  # 105 * 2
    assert evidences[0].evidence_type == EvidenceType.SOCIAL_VOICE


@pytest.mark.asyncio
async def test_fake_youtube_collector_exceeded_error() -> None:
    collector = FakeYouTubeCollector(simulate_quota_exceeded=True)
    with pytest.raises(YouTubeQuotaExceededError, match="Quota diária da API do YouTube esgotada"):
        await collector.collect(analysis_id="an-123", search_terms=["termo"])


# --- Apify com Pinagem de Actors e Orçamento ---


@pytest.mark.asyncio
async def test_apify_pinned_actors() -> None:
    registry = ApifyActorRegistry.from_settings(
        AppSettings(
            _env_file=None,
            APIFY_ACTOR_LINKEDIN_JOBS="curious_coder/linkedin-jobs-scraper@1.7.18",
            APIFY_ACTOR_GOOGLE_SEARCH="apify/google-search-scraper@0.0.473",
        )
    )

    assert registry.require("linkedin_jobs").build == "1.7.18"
    assert registry.require("google_search").actor_id == "apify/google-search-scraper"


@pytest.mark.asyncio
async def test_fake_apify_collector_budget_tracking(sample_plan: ResearchPlan) -> None:
    collector = FakeApifyCollector(cost_per_term=0.05)
    evidences = await collector.collect(
        analysis_id="an-123",
        search_terms=["subscritor de riscos", "atuario pleno"],
        plan=sample_plan,
    )

    assert len(evidences) == 2
    assert evidences[0].evidence_type == EvidenceType.JOB_MARKET
    assert sample_plan.spent_usd == 0.10


@pytest.mark.asyncio
async def test_fake_apify_collector_stops_when_budget_exceeded() -> None:
    plan = ResearchPlan(
        analysis_id="an-123",
        tenant_id="ens",
        cache_key="key",
        budget_limit_usd=0.08,  # Apenas suficiente para 1 termo a $0.05
    )
    collector = FakeApifyCollector(cost_per_term=0.05)
    evidences = await collector.collect(
        analysis_id="an-123",
        search_terms=["termo 1", "termo 2", "termo 3"],
        plan=plan,
    )

    assert len(evidences) == 1
    assert plan.spent_usd == 0.05
