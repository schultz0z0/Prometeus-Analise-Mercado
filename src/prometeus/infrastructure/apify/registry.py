"""Registry explícito de capabilities e Actors Apify autorizados pelo deployment."""

from __future__ import annotations

import math
import re
import unicodedata
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
    country = _non_empty_string(call.parameters.get("country"), "br").lower()
    language = _non_empty_string(call.parameters.get("language"), "pt-BR")
    normalized_language = (
        unicodedata.normalize("NFKD", language).encode("ascii", "ignore").decode().lower()
    )
    if normalized_language == "pt" or normalized_language.startswith("portugues"):
        language = "pt-BR"
    else:
        supported = "af sq sm ar az eu be bn bh bs bg ca zh-CN zh-TW hr cs da nl en eo et fo fi fr fy gl ka de el gu iw hi hu is id ia ga it ja jw kn ko la lv lt mk ms ml mt mr ne no nn oc fa pl pt-BR pt-PT pa ro ru gd sr si sk sl es su sw sv tl ta te th ti tr uk ur uz vi cy xh zu".split()
        by_lower = {code.lower(): code for code in supported}
        language = by_lower.get(language.lower().replace("_", "-"), "")
        if not language:
            raise ActorConfigurationError(
                "A busca Google exige um código de idioma suportado, como pt-BR."
            )
    return {
        "queries": call.query,
        "maxPagesPerQuery": max(1, math.ceil(call.max_items / 10)),
        "countryCode": country,
        "languageCode": language,
    }


def _web_crawler_input(call: PlannedToolCall) -> dict[str, Any]:
    max_depth = call.parameters.get("max_crawl_depth", 0)
    return {
        "startUrls": [{"url": url} for url in _urls(call)],
        "maxCrawlPages": call.max_items,
        "maxCrawlDepth": max_depth,
        "crawlerType": "playwright:adaptive",
        "proxyConfiguration": {"useApifyProxy": True},
    }


def _meta_ads_input(call: PlannedToolCall) -> dict[str, Any]:
    normalized = (
        unicodedata.normalize("NFKD", call.query).encode("ascii", "ignore").decode("ascii").lower()
    )
    educational = re.search(
        r"\b(cursos?|mba|pos|graduacao|especializacao|faculdade|escola|universidade)\b", normalized
    )
    payload: dict[str, Any] = {
        "query": call.query if educational else f"curso {call.query}",
        "maxItems": call.max_items,
        "country": _non_empty_string(call.parameters.get("country"), "BR"),
        "activeStatus": _non_empty_string(call.parameters.get("active_status"), "active"),
    }
    if category := call.parameters.get("category"):
        payload["category"] = category
    return payload


def _linkedin_input(call: PlannedToolCall) -> dict[str, Any]:
    raw_locations = call.parameters.get("locations", call.parameters.get("location", ["Brazil"]))
    if isinstance(raw_locations, str):
        raw_locations = [raw_locations]
    if not isinstance(raw_locations, list):
        raw_locations = ["Brazil"]
    locations = [
        "Brazil" if str(loc).strip().lower() in {"brasil", "br", "brazil"} else str(loc).strip()
        for loc in raw_locations
        if str(loc).strip()
    ] or ["Brazil"]
    search_query = call.query.strip()
    if call.parameters.get("broaden_query") is True:
        if "segur" in search_query.lower():
            search_query = "seguros"
        else:
            tokens = [
                tok
                for tok in re.findall(r"[A-Za-zÀ-ÿ0-9]+", search_query)
                if len(tok) >= 4
                and tok.lower()
                not in {"para", "como", "curso", "gestao", "gestão", "juridico", "jurídico"}
            ]
            search_query = tokens[0] if tokens else search_query
    return {
        "searchQuery": search_query,
        "locations": locations,
        "maxItems": call.max_items,
    }


def _linkedin_jobs_input(call: PlannedToolCall) -> dict[str, Any]:
    location = _non_empty_string(call.parameters.get("location"), "Brazil")
    if location.lower() in {"brasil", "brazil", "br"}:
        location = "Brazil"
    payload: dict[str, Any] = {
        "keywords": call.query,
        "location": location,
        "limitPerSource": call.max_items,
    }
    geo_id = call.parameters.get("geo_id")
    if isinstance(geo_id, str) and geo_id.isdigit():
        payload["geoId"] = geo_id
    distance = call.parameters.get("distance")
    if isinstance(distance, int | float) and distance > 0:
        payload["distance"] = distance
    return payload


def _instagram_input(call: PlannedToolCall) -> dict[str, Any]:
    search_type = _non_empty_string(call.parameters.get("search_type"), "hashtag")
    search_query = call.query.lstrip("#").strip()
    if search_type == "hashtag":
        normalized = (
            unicodedata.normalize("NFKD", search_query)
            .encode("ascii", "ignore")
            .decode("ascii")
            .lower()
        )
        tokens = [
            tok
            for tok in re.findall(r"[a-z0-9]+", normalized)
            if tok not in {"de", "da", "do", "em", "para", "com", "pos", "mba", "curso"}
        ]
        if tokens:
            search_query = "".join(tokens)
        else:
            search_query = re.sub(r"[^a-z0-9]", "", normalized)
            if not search_query:
                raise ActorConfigurationError(
                    "A busca de hashtag exige um termo profissional válido."
                )
    return {
        "search": search_query,
        "searchType": search_type,
        "resultsType": _non_empty_string(call.parameters.get("results_type"), "posts"),
        "resultsLimit": call.max_items,
    }


def _tiktok_input(call: PlannedToolCall) -> dict[str, Any]:
    section = _non_empty_string(call.parameters.get("search_section"), "/video")
    if section in {"video", "user"}:
        section = f"/{section}"
    elif section not in {"", "/video", "/user"}:
        section = "/video"
    return {
        "searchQueries": [call.query],
        "resultsPerPage": call.max_items,
        "searchSection": section,
    }


def _youtube_comments_input(call: PlannedToolCall) -> dict[str, Any]:
    raw_sort = _non_empty_string(call.parameters.get("sort"), "TOP_COMMENTS").upper()
    sort_map = {
        "TOP": "TOP_COMMENTS",
        "TOP_COMMENTS": "TOP_COMMENTS",
        "NEWEST": "NEWEST_FIRST",
        "NEWEST_FIRST": "NEWEST_FIRST",
    }
    return {
        "startUrls": [{"url": url} for url in _urls(call)],
        "maxComments": call.max_items,
        "sortCommentsBy": sort_map.get(raw_sort, "TOP_COMMENTS"),
    }


def _reddit_input(call: PlannedToolCall) -> dict[str, Any]:
    return {
        "searches": [call.query],
        "maxItems": call.max_items,
        "sort": _non_empty_string(call.parameters.get("sort"), "relevance"),
        "time": _non_empty_string(call.parameters.get("time"), "year"),
    }


def _google_trends_input(call: PlannedToolCall) -> dict[str, Any]:
    raw_range = str(call.parameters.get("time_range", "")).strip()
    valid_ranges = {
        "",
        "now 1-H",
        "now 4-H",
        "now 1-d",
        "now 7-d",
        "today 1-m",
        "today 3-m",
        "today 5-y",
        "all",
    }
    time_range = raw_range if raw_range in valid_ranges else ""
    terms = call.parameters.get("search_terms")
    if not isinstance(terms, list):
        terms = call.query.split(",")
    terms = list(
        dict.fromkeys(term.strip() for term in terms if isinstance(term, str) and term.strip())
    )
    if not terms:
        raise ActorConfigurationError("Google Trends exige ao menos um termo de busca.")
    return {
        "searchTerms": terms[:5],
        "maxItems": call.max_items,
        "geo": _non_empty_string(call.parameters.get("geo"), "BR"),
        "timeRange": time_range,
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
