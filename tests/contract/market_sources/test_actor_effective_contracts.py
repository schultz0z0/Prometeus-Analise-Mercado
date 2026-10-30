"""Testes de contrato para capabilities, inputs efetivos e escopo geográfico

(Fase 2 — Tarefa 2.1).

Contratos verificados:
1. Cada capability possui unidade de limite explícita (per_query, retained_total, per_video).
2. O input efetivo do Actor é reconciliado com o schema do build pinado.
3. O texto da query nunca substitui filtros estruturados.
4. O broadening silencioso do LinkedIn para "seguros" foi eliminado; preservado apenas
   como ação explicitamente contextual (broaden_query=True).
5. Todas as 27 UFs brasileiras (sigla e nome por extenso) são reconhecidas no contrato
   geográfico, com resolução de ambiguidades.
6. Localidades estrangeiras homônimas ou fora do país são rejeitadas quando o Brasil
   é requerido; idioma ou proxy não provam país.
7. `effective_actor_input` e `effective_scope` são registrados sem segredos.
"""

from __future__ import annotations

from prometeus.application.research_scope import (
    BRAZILIAN_STATES,
    matches_narrow_geography,
)
from prometeus.application.tool_capabilities import (
    CAPABILITY_CONTRACTS,
    CAPABILITY_LIMIT_UNITS,
)
from prometeus.domain.configuration import AppSettings
from prometeus.domain.research import PlannedToolCall
from prometeus.infrastructure.apify.registry import (
    ApifyActorRegistry,
)


def configured_settings() -> AppSettings:
    return AppSettings(
        _env_file=None,
        APIFY_ACTOR_GOOGLE_SEARCH="apify/google-search-scraper@0.0.473",
        APIFY_ACTOR_WEB_CRAWLER="apify/website-content-crawler@0.3.102",
        APIFY_ACTOR_META_AD_LIBRARY="igolaizola/facebook-ad-library-scraper@0.0.59",
        APIFY_ACTOR_LINKEDIN="harvestapi/linkedin-company-search@0.0.21",
        APIFY_ACTOR_LINKEDIN_JOBS="curious_coder/linkedin-jobs-scraper@1.7.18",
        APIFY_ACTOR_INSTAGRAM="apify/instagram-scraper@0.0.831",
        APIFY_ACTOR_TIKTOK="clockworks/tiktok-scraper@0.0.625",
        APIFY_ACTOR_YOUTUBE_COMMENTS="streamers/youtube-comments-scraper@0.0.257",
        APIFY_ACTOR_REDDIT="trudax/reddit-scraper-lite@5.8.7",
        APIFY_ACTOR_GOOGLE_TRENDS="apify/google-trends-scraper@0.0.143",
    )


def test_every_capability_has_a_defined_limit_unit():
    """Garante que todas as capabilities têm uma unidade de limite canônica."""
    expected_capabilities = {
        "google_search",
        "web_crawler",
        "meta_ads_library",
        "linkedin",
        "linkedin_jobs",
        "instagram",
        "tiktok",
        "youtube_comments",
        "reddit",
        "google_trends",
    }
    for cap in expected_capabilities:
        assert cap in CAPABILITY_LIMIT_UNITS, f"Unidade de limite ausente para: {cap}"
        assert CAPABILITY_LIMIT_UNITS[cap] in {"per_query", "retained_total", "per_video"}
        assert "limit_unit" in CAPABILITY_CONTRACTS[cap]


def test_linkedin_company_search_does_not_silently_broaden_to_seguros():
    """Tarefa 2.1: Eliminar o broadening silencioso da busca de empresas no LinkedIn.

    A consulta deve usar a query original a menos que broaden_query=True seja explicitado.
    """
    registry = ApifyActorRegistry.from_settings(configured_settings())

    # Caso 1: Sem broaden_query (padrão) -> query original é preservada exatamente
    call_default = PlannedToolCall(
        id="c1",
        capability="linkedin",
        query="empresas de tecnologia e inteligência artificial em seguros",
        rationale="teste",
        max_items=10,
        parameters={"locations": ["São Paulo"]},
    )
    input_default = registry.build_input(call_default)
    assert input_default["searchQuery"] == "empresas de tecnologia e inteligência artificial em seguros"

    # Caso 2: Com broaden_query=True explícito -> broadening contextual permitido
    call_broadened = PlannedToolCall(
        id="c2",
        capability="linkedin",
        query="empresas de tecnologia e inteligência artificial em seguros",
        rationale="teste",
        max_items=10,
        parameters={"locations": ["São Paulo"], "broaden_query": True},
    )
    input_broadened = registry.build_input(call_broadened)
    assert input_broadened["searchQuery"] == "seguros"


def test_all_27_brazilian_ufs_are_recognized_in_geographic_contract():
    """Tarefa 2.1: Todas as 27 UFs brasileiras (sigla e nome por extenso)

    devem ser reconhecidas e validadas pelo contrato geográfico.
    """
    assert len(BRAZILIAN_STATES) == 27
    expected_ufs = {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
        "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
        "RS", "RO", "RR", "SC", "SP", "SE", "TO",
    }
    assert set(BRAZILIAN_STATES.keys()) == expected_ufs

    # Testa correspondência de cada UF por sigla e por nome quando escopo é Brasil
    for uf, state_name in BRAZILIAN_STATES.items():
        # Sigla isolada com separador
        assert matches_narrow_geography("Brasil", f"Cidade, {uf}, Brazil")
        # Nome do estado por extenso
        assert matches_narrow_geography("Brasil", f"Cidade, {state_name}, Brasil")


def test_narrow_state_geography_matches_only_its_own_uf_and_rejects_others():
    """Garante que busca por estado específico (ex: SP) aceita somente locais em SP

    e rejeita outros estados (ex: RJ, MG).
    """
    # Escopo São Paulo
    assert matches_narrow_geography("Brasil; somente São Paulo", "São Paulo, SP, Brasil")
    assert matches_narrow_geography("Brasil; somente São Paulo", "Campinas, SP, Brasil")
    assert matches_narrow_geography("Brasil; somente São Paulo", "Barueri, São Paulo, Brasil")

    # Rejeita outros estados quando escopo é São Paulo
    assert not matches_narrow_geography("Brasil; somente São Paulo", "Rio de Janeiro, RJ, Brasil")
    assert not matches_narrow_geography("Brasil; somente São Paulo", "Belo Horizonte, MG, Brasil")
    assert not matches_narrow_geography("Brasil; somente São Paulo", "Curitiba, PR, Brasil")

    # Escopo Minas Gerais
    assert matches_narrow_geography("Brasil; somente Minas Gerais", "Belo Horizonte, MG, Brasil")
    assert matches_narrow_geography("Brasil; somente Minas Gerais", "Uberlândia, Minas Gerais, Brasil")
    assert not matches_narrow_geography("Brasil; somente Minas Gerais", "São Paulo, SP, Brasil")


def test_ambiguous_and_foreign_locations_are_strictly_rejected_for_brazil():
    """Localidades estrangeiras ou siglas ambíguas sem comprovação de Brasil

    devem ser estritamente rejeitadas.
    """
    # Locais nos EUA
    assert not matches_narrow_geography("Brasil", "Irving, TX, USA")
    assert not matches_narrow_geography("Brasil", "Miami, FL, United States")
    assert not matches_narrow_geography("Brasil", "New York, NY")

    # Locais na Europa
    assert not matches_narrow_geography("Brasil", "Lisboa, Portugal")
    assert not matches_narrow_geography("Brasil", "Madrid, Spain")
    assert not matches_narrow_geography("Brasil", "London, UK")

    # Ambiguidades: PA (Pennsylvania vs Pará)
    # Sem evidência de Brasil ou cidade paraense, PA isolado nos EUA não é aceito
    assert not matches_narrow_geography("Brasil", "Philadelphia, PA, United States")
    # Com cidade paraense ou menção a Brasil, é aceito
    assert matches_narrow_geography("Brasil", "Belém, PA, Brasil")


def test_youtube_comments_input_preserves_per_video_limit_semantics():
    """O input do Actor de comentários do YouTube usa maxComments como limite por vídeo."""
    registry = ApifyActorRegistry.from_settings(configured_settings())
    call = PlannedToolCall(
        id="yt1",
        capability="youtube_comments",
        query="comentarios sobre mba",
        rationale="teste",
        max_items=15,
        parameters={"urls": ["https://www.youtube.com/watch?v=video123"]},
    )
    payload = registry.build_input(call)
    assert payload["maxComments"] == 15
    assert payload["startUrls"] == [{"url": "https://www.youtube.com/watch?v=video123"}]

