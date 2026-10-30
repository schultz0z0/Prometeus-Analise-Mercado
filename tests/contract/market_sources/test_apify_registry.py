from __future__ import annotations

import pytest

from prometeus.domain.configuration import AppSettings
from prometeus.domain.research import PlannedToolCall
from prometeus.infrastructure.apify.registry import (
    ActorConfigurationError,
    ApifyActorRegistry,
)


def configured_settings(**overrides: str) -> AppSettings:
    values = {
        "APIFY_ACTOR_GOOGLE_SEARCH": "apify/google-search-scraper@0.0.473",
        "APIFY_ACTOR_WEB_CRAWLER": "apify/website-content-crawler@0.3.102",
        "APIFY_ACTOR_META_AD_LIBRARY": ("igolaizola/facebook-ad-library-scraper@0.0.59"),
        "APIFY_ACTOR_LINKEDIN": "harvestapi/linkedin-company-search@0.0.21",
        "APIFY_ACTOR_LINKEDIN_JOBS": "curious_coder/linkedin-jobs-scraper@1.7.18",
        "APIFY_ACTOR_INSTAGRAM": "apify/instagram-scraper@0.0.831",
        "APIFY_ACTOR_TIKTOK": "clockworks/tiktok-scraper@0.0.625",
        "APIFY_ACTOR_YOUTUBE_COMMENTS": ("streamers/youtube-comments-scraper@0.0.257"),
        "APIFY_ACTOR_REDDIT": "trudax/reddit-scraper-lite@5.8.7",
        "APIFY_ACTOR_GOOGLE_TRENDS": "apify/google-trends-scraper@0.0.143",
    }
    values.update(overrides)
    return AppSettings(_env_file=None, **values)


def test_registry_contains_only_explicitly_configured_pinned_actors() -> None:
    registry = ApifyActorRegistry.from_settings(
        AppSettings(
            _env_file=None,
            APIFY_ACTOR_GOOGLE_SEARCH="apify/google-search-scraper@0.0.473",
        )
    )

    assert registry.capabilities == ("google_search",)
    spec = registry.require("google_search")
    assert spec.actor_id == "apify/google-search-scraper"
    assert spec.build == "0.0.473"
    assert spec.actor_path == "apify~google-search-scraper"

    with pytest.raises(ActorConfigurationError, match="não está configurada"):
        registry.require("linkedin_jobs")


def test_google_normalizes_portuguese_description_instead_of_sending_prose_as_locale():
    registry = ApifyActorRegistry.from_settings(configured_settings())
    payload = registry.build_input(
        PlannedToolCall(
            id="locale",
            capability="google_search",
            query="MBA seguros",
            rationale="teste",
            parameters={
                "country": "BR",
                "language": "Português; disciplinas ministradas em português",
            },
        )
    )
    assert payload["languageCode"] == "pt-BR"


def test_google_rejects_unknown_language_before_paid_execution():
    registry = ApifyActorRegistry.from_settings(configured_settings())
    with pytest.raises(ActorConfigurationError, match="idioma"):
        registry.build_input(
            PlannedToolCall(
                id="locale",
                capability="google_search",
                query="MBA",
                rationale="teste",
                parameters={"language": "nonsense locale"},
            )
        )


@pytest.mark.parametrize(
    "actor_ref",
    [
        "apify/google-search-scraper",
        "apify/google-search-scraper@latest",
        "google-search-scraper@0.0.473",
        "apify/google-search-scraper@",
    ],
)
def test_registry_rejects_unpinned_or_malformed_actor_references(actor_ref: str) -> None:
    with pytest.raises(ActorConfigurationError):
        ApifyActorRegistry.from_settings(
            AppSettings(_env_file=None, APIFY_ACTOR_GOOGLE_SEARCH=actor_ref)
        )


def test_registry_builds_actor_specific_inputs_without_forwarding_unknown_parameters() -> None:
    registry = ApifyActorRegistry.from_settings(configured_settings())

    google = registry.build_input(
        PlannedToolCall(
            id="google",
            capability="google_search",
            query="MBA inteligência artificial seguros Brasil",
            rationale="mapear concorrentes",
            max_items=30,
            parameters={"country": "BR", "language": "pt", "token": "must-not-leak"},
        )
    )
    jobs = registry.build_input(
        PlannedToolCall(
            id="jobs",
            capability="linkedin_jobs",
            query="subscritor inteligência artificial",
            rationale="medir demanda ocupacional",
            max_items=40,
            parameters={"location": "Brasil", "distance": 50},
        )
    )

    assert google == {
        "queries": "MBA inteligência artificial seguros Brasil",
        "maxPagesPerQuery": 3,
        "countryCode": "br",
        "languageCode": "pt-BR",
    }
    assert jobs == {
        "keywords": "subscritor inteligência artificial",
        "location": "Brazil",
        "distance": 50,
        "limitPerSource": 40,
    }


def test_jobs_location_alias_and_explicit_geo_id_use_official_actor_fields() -> None:
    registry = ApifyActorRegistry.from_settings(configured_settings())
    jobs = registry.build_input(
        PlannedToolCall(
            capability="linkedin_jobs",
            query="Advogado de Seguros",
            rationale="vagas nacionais",
            parameters={"location": "BR", "geo_id": "106057199"},
        )
    )
    assert jobs["location"] == "Brazil"
    assert jobs["geoId"] == "106057199"


def test_meta_ads_search_includes_educational_intent_without_rewriting_existing_intent() -> None:
    registry = ApifyActorRegistry.from_settings(configured_settings())

    def build(query: str) -> str:
        return registry.build_input(
            PlannedToolCall(
                capability="meta_ads_library", query=query, rationale="concorrentes educacionais"
            )
        )["query"]

    assert build("direito securitário") == "curso direito securitário"
    assert build("MBA seguros") == "MBA seguros"


def test_instagram_preserves_niche_in_hashtag_instead_of_only_first_word() -> None:
    registry = ApifyActorRegistry.from_settings(configured_settings())
    payload = registry.build_input(
        PlannedToolCall(
            capability="instagram", query="Direito Securitário", rationale="voz profissional"
        )
    )
    assert payload["search"] == "direitosecuritario"
    assert payload["searchType"] == "hashtag"


def test_url_based_actor_requires_urls_from_the_validated_plan() -> None:
    registry = ApifyActorRegistry.from_settings(configured_settings())
    call = PlannedToolCall(
        capability="web_crawler",
        query="concorrentes selecionados",
        rationale="ler ofertas",
        parameters={},
    )

    with pytest.raises(ActorConfigurationError, match="URLs"):
        registry.build_input(call)


def test_unknown_capability_is_never_authorized_by_actor_id_in_parameters() -> None:
    registry = ApifyActorRegistry.from_settings(configured_settings())
    call = PlannedToolCall(
        capability="arbitrary_scraper",
        query="dados",
        rationale="não autorizado",
        parameters={"actor_id": "someone/dangerous-actor@1.0.0"},
    )

    with pytest.raises(ActorConfigurationError, match="allowlist"):
        registry.build_input(call)
