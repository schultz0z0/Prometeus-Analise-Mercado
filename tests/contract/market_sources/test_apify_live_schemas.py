from __future__ import annotations

import os
from typing import Any

import httpx
import pytest

from prometeus.domain.configuration import AppSettings
from prometeus.infrastructure.apify.registry import ApifyActorRegistry

pytestmark = pytest.mark.skipif(
    os.getenv("PROMETEUS_RUN_LIVE_APIFY_TESTS") != "1",
    reason="Live Apify schema checks require explicit opt-in.",
)


EXPECTED_INPUT_FIELDS: dict[str, set[str]] = {
    "google_search": {"queries", "maxPagesPerQuery", "countryCode", "languageCode"},
    "web_crawler": {"startUrls", "maxCrawlPages", "crawlerType", "proxyConfiguration"},
    "meta_ads_library": {"query", "maxItems", "country", "activeStatus"},
    "linkedin": {"searchQuery", "locations", "maxItems"},
    "linkedin_jobs": {"keywords", "location", "distance", "limitPerSource"},
    "instagram": {"search", "searchType", "resultsType", "resultsLimit"},
    "tiktok": {"searchQueries", "resultsPerPage", "searchSection"},
    "youtube_comments": {"startUrls", "maxComments", "sortCommentsBy"},
    "reddit": {"searches", "maxItems", "sort", "time"},
    "google_trends": {"searchTerms", "maxItems", "geo", "timeRange"},
}


@pytest.mark.asyncio
async def test_configured_actor_builds_and_input_schemas_are_still_current() -> None:
    settings = AppSettings()
    registry = ApifyActorRegistry.from_settings(settings)
    required_capabilities = set(settings.required_market_sources)
    capabilities = required_capabilities | ({"google_trends"} & set(registry.capabilities))

    assert required_capabilities <= set(registry.capabilities)

    headers = {"Accept": "application/json"}
    if settings.APIFY_TOKEN.strip():
        headers["Authorization"] = f"Bearer {settings.APIFY_TOKEN.strip()}"

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        for capability in sorted(capabilities):
            spec = registry.require(capability)
            response = await client.get(
                f"{settings.APIFY_BASE_URL.rstrip('/')}/actors/{spec.actor_path}/builds/default"
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()["data"]
            actor_input = payload["actorDefinition"]["input"]
            fields = set(actor_input.get("properties", {}))

            assert payload["status"] == "SUCCEEDED"
            assert payload["buildNumber"] == spec.build
            assert EXPECTED_INPUT_FIELDS[capability] <= fields
