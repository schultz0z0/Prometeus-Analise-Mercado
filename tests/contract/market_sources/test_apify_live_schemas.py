from __future__ import annotations

import os
from typing import Any

import httpx
import pytest

from prometeus.domain.configuration import AppSettings
from prometeus.domain.research import PlannedToolCall
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


def assert_input_value(value: Any, schema: dict[str, Any], path: str) -> None:
    """Check supported Actor input constraints; never start an Actor."""
    if "enum" in schema:
        assert value in schema["enum"], f"{path}: valor fora do enum do Actor"
    kind = schema.get("type")
    if kind == "string":
        assert isinstance(value, str), path
    elif kind == "integer":
        assert isinstance(value, int) and not isinstance(value, bool), path
    elif kind == "number":
        assert isinstance(value, (int, float)) and not isinstance(value, bool), path
    elif kind == "boolean":
        assert isinstance(value, bool), path
    elif kind == "array":
        assert isinstance(value, list), path
        if isinstance(schema.get("items"), dict):
            for index, item in enumerate(value):
                assert_input_value(item, schema["items"], f"{path}[{index}]")
    elif kind == "object":
        assert isinstance(value, dict), path
        assert set(schema.get("required", [])) <= set(value), path
        for key, item in value.items():
            if key in schema.get("properties", {}):
                assert_input_value(item, schema["properties"][key], f"{path}.{key}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema:
            assert value >= schema["minimum"], path
        if "maximum" in schema:
            assert value <= schema["maximum"], path


@pytest.mark.asyncio
async def test_configured_actor_builds_and_input_schemas_are_still_current() -> None:
    settings = AppSettings()
    registry = ApifyActorRegistry.from_settings(settings)
    required_capabilities = set(settings.required_market_sources)
    capabilities = set(registry.capabilities)

    assert required_capabilities <= set(registry.capabilities)

    headers = {"Accept": "application/json"}
    if settings.APIFY_TOKEN.strip():
        headers["Authorization"] = f"Bearer {settings.APIFY_TOKEN.strip()}"

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        for capability in sorted(capabilities):
            assert capability in EXPECTED_INPUT_FIELDS, (
                f"Capability sem contrato de schema: {capability}"
            )
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
            call = PlannedToolCall(
                id=f"contract-{capability}",
                capability=capability,
                query="gestão de seguros",
                rationale="Validar entrada sem executar coleta",
                max_items=5,
                parameters={
                    "country": "BR",
                    "language": "pt-BR",
                    "location": "Brazil",
                    "geo": "BR",
                    "urls": ["https://www.youtube.com/watch?v=contract-test"]
                    if capability == "youtube_comments"
                    else ["https://example.org/curso"],
                },
            )
            actor_payload = registry.build_input(call)
            assert set(actor_payload) <= fields, f"{capability}: campo não declarado pelo Actor"
            assert set(actor_input.get("required", [])) <= set(actor_payload), capability
            for name, value in actor_payload.items():
                assert_input_value(value, actor_input["properties"][name], f"{capability}.{name}")
