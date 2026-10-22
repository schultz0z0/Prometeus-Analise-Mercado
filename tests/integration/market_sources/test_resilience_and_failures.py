"""Testes de resiliência e comportamento de falha para fontes externas (Task 12).

Simula timeout, erro 429, schema drift, resultados vazios e custo excedido.
"""

import pytest

from prometeus.application.sanitization import EvidenceSanitizer
from prometeus.domain.ports.market_sources import (
    ResearchPlan,
)
from prometeus.infrastructure.apify.client import FakeApifyCollector
from prometeus.infrastructure.google_ads.client import FakeGoogleAdsCollector
from prometeus.infrastructure.trends.client import FakeTrendsCollector
from prometeus.infrastructure.youtube.client import (
    FakeYouTubeCollector,
    YouTubeQuotaExceededError,
)


@pytest.mark.asyncio
async def test_empty_results_handling() -> None:
    """Quando o provedor retorna lista vazia de resultados, a análise não deve falhar."""
    empty_ads_collector = FakeGoogleAdsCollector(canned_metrics={})
    evidences = await empty_ads_collector.collect(
        analysis_id="an-empty",
        search_terms=[],
    )
    assert len(evidences) == 0


@pytest.mark.asyncio
async def test_timeout_and_transport_error_resilience() -> None:
    """Falhas transitórias em um coletor devem ser capturáveis de forma isolada."""
    failing_trends = FakeTrendsCollector(simulate_error=True)

    with pytest.raises(ConnectionError, match="Falha de conexão com Google Trends"):
        await failing_trends.collect(analysis_id="an-fail", search_terms=["termo"])


@pytest.mark.asyncio
async def test_budget_exceeded_graceful_stop() -> None:
    """Custo excedido interrompe novas chamadas ao Apify sem corromper o estado do plano."""
    plan = ResearchPlan(
        analysis_id="an-budget",
        tenant_id="ens",
        cache_key="key",
        budget_limit_usd=0.10,  # Permite apenas 2 termos ($0.05 cada)
    )

    collector = FakeApifyCollector(cost_per_term=0.05)
    evidences = await collector.collect(
        analysis_id="an-budget",
        search_terms=["termo 1", "termo 2", "termo 3", "termo 4"],
        plan=plan,
    )

    # Coletou exatamente 2 antes de estourar o limite
    assert len(evidences) == 2
    assert plan.spent_usd == 0.10
    # O próximo termo não foi executado
    assert collector.call_count == 2


@pytest.mark.asyncio
async def test_youtube_quota_exceeded_isolation() -> None:
    """Exaustão de quota da API do YouTube é detectada e tratada com tipo específico."""
    collector = FakeYouTubeCollector(simulate_quota_exceeded=True)
    with pytest.raises(YouTubeQuotaExceededError, match="Quota diária da API do YouTube esgotada"):
        await collector.collect(analysis_id="an-quota", search_terms=["termo"])


def test_schema_drift_in_raw_payload_handled_safely() -> None:
    """Schema drift (campos novos, inesperados ou nulos no payload) não quebra o sanitizador."""
    sanitizer = EvidenceSanitizer()

    unusual_payload = {
        "unexpected_field_nested": {"new_key": None, "numeric_code": 9999},
        "array_mixed": [1, "texto normal", None, {"sub": "valor"}],
        "weird_unicode": "Test \x00 null bytes and \u202e reversed text",
    }

    sanitized, score = sanitizer.sanitize_payload(unusual_payload)

    assert "unexpected_field_nested" in sanitized
    assert sanitized["unexpected_field_nested"]["numeric_code"] == 9999
    assert score > 0.0
