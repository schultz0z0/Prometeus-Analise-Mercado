"""Registry explícito de capabilities e Actors Apify autorizados pelo deployment."""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from prometeus.domain.configuration import AppSettings
from prometeus.domain.ports.market_sources import EvidenceType
from prometeus.domain.research import PlannedToolCall


class ActorConfigurationError(ValueError):
    """Configuração de Actor ausente, inválida ou fora da allowlist."""


_ACTOR_REF_PATTERN = re.compile(
    r"^(?P<owner>[A-Za-z0-9_-]+)/(?P<name>[A-Za-z0-9_-]+)"
    r"@(?P<build>[0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,5})$"
)


@dataclass(frozen=True)
class ApifyActorSpec:
    capability: str
    actor_id: str
    build: str
    evidence_type: EvidenceType
    input_builder: Callable[[PlannedToolCall], dict[str, Any]]

    @property
    def actor_path(self) -> str:
        return self.actor_id.replace("/", "~", 1)


def _non_empty_string(value: Any, default: str) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _urls(call: PlannedToolCall) -> list[str]:
    candidate = call.parameters.get("urls", call.parameters.get("start_urls", []))
    if isinstance(candidate, str):
        candidate = [candidate]
    if not isinstance(candidate, list):
        candidate = []
    urls = [url.strip() for url in candidate if isinstance(url, str) and url.strip()]
    if not urls:
        raise ActorConfigurationError(
            f"A capability '{call.capability}' exige URLs validadas no plano de pesquisa."
        )
    return urls[: call.max_items]


def _google_search_input(call: PlannedToolCall) -> dict[str, Any]:
    return {
        "queries": call.query,
        "maxPagesPerQuery": max(1, math.ceil(call.max_items / 10)),
        "countryCode": _non_empty_string(call.parameters.get("country"), "BR"),
        "languageCode": _non_empty_string(call.parameters.get("language"), "pt"),
    }


def _web_crawler_input(call: PlannedToolCall) -> dict[str, Any]:
    return {
        "startUrls": [{"url": url} for url in _urls(call)],
        "maxCrawlPages": call.max_items,
        "crawlerType": "playwright:adaptive",
        "proxyConfiguration": {"useApifyProxy": True},
    }


def _meta_ads_input(call: PlannedToolCall) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "query": call.query,
        "maxItems": call.max_items,
        "country": _non_empty_string(call.parameters.get("country"), "BR"),
        "activeStatus": _non_empty_string(call.parameters.get("active_status"), "active"),
    }
    if category := call.parameters.get("category"):
        payload["category"] = category
    return payload


def _linkedin_input(call: PlannedToolCall) -> dict[str, Any]:
    locations = call.parameters.get("locations", call.parameters.get("location", ["Brazil"]))
    if isinstance(locations, str):
        locations = [locations]
    return {
        "searchQuery": call.query,
        "locations": locations,
        "maxItems": call.max_items,
    }


def _linkedin_jobs_input(call: PlannedToolCall) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "keywords": call.query,
        "location": _non_empty_string(call.parameters.get("location"), "Brasil"),
        "limitPerSource": call.max_items,
    }
    distance = call.parameters.get("distance")
    if isinstance(distance, int | float) and distance > 0:
        payload["distance"] = distance
    return payload


def _instagram_input(call: PlannedToolCall) -> dict[str, Any]:
    return {
        "search": call.query,
        "searchType": _non_empty_string(call.parameters.get("search_type"), "hashtag"),
        "resultsType": _non_empty_string(call.parameters.get("results_type"), "posts"),
        "resultsLimit": call.max_items,
    }


def _tiktok_input(call: PlannedToolCall) -> dict[str, Any]:
    return {
        "searchQueries": [call.query],
        "resultsPerPage": call.max_items,
        "searchSection": _non_empty_string(call.parameters.get("search_section"), "video"),
    }


def _youtube_comments_input(call: PlannedToolCall) -> dict[str, Any]:
    return {
        "startUrls": [{"url": url} for url in _urls(call)],
        "maxComments": call.max_items,
        "sortCommentsBy": _non_empty_string(call.parameters.get("sort"), "top"),
    }


def _reddit_input(call: PlannedToolCall) -> dict[str, Any]:
    return {
        "searches": [call.query],
        "maxItems": call.max_items,
        "sort": _non_empty_string(call.parameters.get("sort"), "relevance"),
        "time": _non_empty_string(call.parameters.get("time"), "year"),
    }


def _google_trends_input(call: PlannedToolCall) -> dict[str, Any]:
    return {
        "searchTerms": [call.query],
        "maxItems": call.max_items,
        "geo": _non_empty_string(call.parameters.get("geo"), "BR"),
        "timeRange": _non_empty_string(call.parameters.get("time_range"), "today 12-m"),
    }


def _google_analytics_input(call: PlannedToolCall) -> dict[str, Any]:
    property_id = call.parameters.get("property_id")
    if not isinstance(property_id, str) or not property_id.strip():
        raise ActorConfigurationError(
            "A capability 'google_analytics' exige property_id autorizado pelo tenant."
        )
    return {
        "propertyId": property_id.strip(),
        "query": call.query,
        "maxItems": call.max_items,
        "dateRange": _non_empty_string(call.parameters.get("date_range"), "last_90_days"),
    }


@dataclass(frozen=True)
class _CapabilityDefinition:
    setting_name: str
    evidence_type: EvidenceType
    input_builder: Callable[[PlannedToolCall], dict[str, Any]]


CAPABILITY_DEFINITIONS: dict[str, _CapabilityDefinition] = {
    "google_search": _CapabilityDefinition(
        "APIFY_ACTOR_GOOGLE_SEARCH", EvidenceType.OFFER, _google_search_input
    ),
    "web_crawler": _CapabilityDefinition(
        "APIFY_ACTOR_WEB_CRAWLER", EvidenceType.OFFER, _web_crawler_input
    ),
    "meta_ads_library": _CapabilityDefinition(
        "APIFY_ACTOR_META_AD_LIBRARY", EvidenceType.PAID_COMPETITION, _meta_ads_input
    ),
    "linkedin": _CapabilityDefinition("APIFY_ACTOR_LINKEDIN", EvidenceType.OFFER, _linkedin_input),
    "linkedin_jobs": _CapabilityDefinition(
        "APIFY_ACTOR_LINKEDIN_JOBS", EvidenceType.JOB_MARKET, _linkedin_jobs_input
    ),
    "instagram": _CapabilityDefinition(
        "APIFY_ACTOR_INSTAGRAM", EvidenceType.SOCIAL_VOICE, _instagram_input
    ),
    "tiktok": _CapabilityDefinition("APIFY_ACTOR_TIKTOK", EvidenceType.SOCIAL_VOICE, _tiktok_input),
    "youtube_comments": _CapabilityDefinition(
        "APIFY_ACTOR_YOUTUBE_COMMENTS", EvidenceType.SOCIAL_VOICE, _youtube_comments_input
    ),
    "reddit": _CapabilityDefinition("APIFY_ACTOR_REDDIT", EvidenceType.SOCIAL_VOICE, _reddit_input),
    "google_trends": _CapabilityDefinition(
        "APIFY_ACTOR_GOOGLE_TRENDS", EvidenceType.TRENDS, _google_trends_input
    ),
    "google_analytics": _CapabilityDefinition(
        "APIFY_ACTOR_GOOGLE_ANALYTICS", EvidenceType.SEARCH_VOLUME, _google_analytics_input
    ),
}


class ApifyActorRegistry:
    """Allowlist resolvida exclusivamente da configuração do deployment."""

    def __init__(self, specs: dict[str, ApifyActorSpec]) -> None:
        self._specs = dict(specs)

    @classmethod
    def from_settings(cls, settings: AppSettings) -> ApifyActorRegistry:
        specs: dict[str, ApifyActorSpec] = {}
        for capability, definition in CAPABILITY_DEFINITIONS.items():
            raw = str(getattr(settings, definition.setting_name, "")).strip()
            if not raw:
                continue
            match = _ACTOR_REF_PATTERN.fullmatch(raw)
            if match is None or match.group("build") == "latest":
                raise ActorConfigurationError(
                    f"{definition.setting_name} deve usar owner/name@build-number pinado."
                )
            specs[capability] = ApifyActorSpec(
                capability=capability,
                actor_id=f"{match.group('owner')}/{match.group('name')}",
                build=match.group("build"),
                evidence_type=definition.evidence_type,
                input_builder=definition.input_builder,
            )
        return cls(specs)

    @property
    def capabilities(self) -> tuple[str, ...]:
        return tuple(sorted(self._specs))

    def require(self, capability: str) -> ApifyActorSpec:
        if capability not in CAPABILITY_DEFINITIONS:
            raise ActorConfigurationError(
                f"A capability '{capability}' não pertence à allowlist Apify."
            )
        spec = self._specs.get(capability)
        if spec is None:
            raise ActorConfigurationError(
                f"A capability '{capability}' não está configurada no deployment."
            )
        return spec

    def build_input(self, call: PlannedToolCall) -> dict[str, Any]:
        return self.require(call.capability).input_builder(call)
