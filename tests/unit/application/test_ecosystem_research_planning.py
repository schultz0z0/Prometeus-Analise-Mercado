"""Testes unitários de planejamento de pesquisa clusterizado por ecossistema institucional (concorrentes fixos + radar setorial)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from prometeus.application.plan_course_research import (
    CourseResearchPlanner,
    build_ecosystem_seed_calls,
    compact_topic_terms,
)
from prometeus.application.skill_registry import SkillRegistry
from prometeus.domain.configuration import AppSettings, load_tenant_config
from prometeus.domain.research import CourseUnderstanding, ResearchTrack
from prometeus.infrastructure.llm.fake import FakeGenerativeModel


def _make_full_settings() -> AppSettings:
    return AppSettings(
        _env_file=None,
        APIFY_REQUIRED_SOURCES="google_search,web_crawler,linkedin_jobs",
        APIFY_ACTOR_GOOGLE_SEARCH="apify/google-search-scraper@0.0.474",
        APIFY_ACTOR_WEB_CRAWLER="apify/website-content-crawler@1.26.2",
        APIFY_ACTOR_LINKEDIN_JOBS="curious_coder/linkedin-jobs-scraper@1.7.18",
        APIFY_ACTOR_INSTAGRAM="apify/instagram-scraper@0.0.340",
        APIFY_MAX_TOTAL_CHARGE_USD_PER_ANALYSIS=5.0,
    )


def test_compact_topic_terms_bounds_word_count() -> None:
    understanding = CourseUnderstanding(
        analysis_id="anl-topic",
        course_title="MBA Executivo em Inteligência Artificial Aplicada à Subscrição de Riscos e Sinistros",
        subject_domains=["inteligência artificial", "subscrição de riscos", "sinistros securitários"],
    )
    compact = compact_topic_terms(understanding, max_tokens=4)
    tokens = compact.split()
    assert 1 <= len(tokens) <= 4


@pytest.mark.asyncio
async def test_planner_injects_clustered_competitors_sector_radar_and_open_web_search() -> None:
    ens_cfg = load_tenant_config(Path("config/tenants/ens.example.yaml"))
    llm = FakeGenerativeModel(
        canned_text=json.dumps(
            {
                "questions": [
                    {
                        "id": "q-1",
                        "question": "Quais ofertas competem pelo aluno?",
                        "track": "direct_competitors",
                        "priority": 1,
                    }
                ],
                "tool_calls": [
                    {
                        "id": "llm-google-site",
                        "capability": "google_search",
                        "query": "site:fgv.br mba seguros inteligencia artificial",
                        "required": True,
                        "rationale": "Busca pontual inicial",
                        "max_items": 10,
                    },
                    {
                        "id": "llm-crawler",
                        "capability": "web_crawler",
                        "query": "Páginas de cursos concorrentes",
                        "required": True,
                        "rationale": "Extrair preços e ementas",
                        "max_items": 8,
                    },
                    {
                        "id": "llm-jobs",
                        "capability": "linkedin_jobs",
                        "query": "subscritor riscos inteligencia artificial",
                        "required": True,
                        "rationale": "Mapear vagas",
                        "max_items": 15,
                    },
                ],
            },
            ensure_ascii=False,
        )
    )
    understanding = CourseUnderstanding(
        analysis_id="anl-ens-1",
        course_title="MBA em Inteligência Artificial Aplicada a Seguros",
        subject_domains=["seguros", "inteligência artificial", "subscrição"],
        target_audiences=["corretores de seguros", "analistas de sinistros"],
        geography="Brasil",
        language="pt-BR",
        institution_name=ens_cfg.institution.display_name,
        institution_domains=ens_cfg.institution.domains,
    )
    planner = CourseResearchPlanner(llm, SkillRegistry("skills"), _make_full_settings())

    plan = await planner.plan(understanding, ecosystem=ens_cfg.ecosystem, budget_limit_usd=5.0)

    google_calls = [c for c in plan.tool_calls if c.capability == "google_search"]
    # 1. Toda chamada google_search respeita <= 5 operadores site: e <= 28 termos
    for gcall in google_calls:
        site_count = gcall.query.lower().count("site:")
        assert site_count <= 5, f"Excesso de operadores site: em '{gcall.query}'"
        assert len(gcall.query.split()) <= 28, f"Query longa demais (>28 tokens): '{gcall.query}'"

    # 2. Os 10 concorrentes educacionais têm seus domínios primários cobertos
    combined_google_queries = " ".join(c.query.lower() for c in google_calls)
    for comp in ens_cfg.ecosystem.competitors:
        assert f"site:{comp.domains[0]}" in combined_google_queries, (
            f"Concorrente '{comp.id}' ({comp.domains[0]}) ausente das buscas clusterizadas"
        )

    # 3. Preserva ao menos 1 busca aberta de mercado sem operador site:
    open_web_calls = [c for c in google_calls if "site:" not in c.query.lower()]
    assert len(open_web_calls) >= 1

    # 4. web_crawler referencia IDs das buscas de concorrentes em depends_on e sem URLs brutas
    comp_search_ids = {
        c.id
        for c in google_calls
        if c.parameters.get("ecosystem_role") == "configured_competitor"
    }
    assert len(comp_search_ids) >= 2
    crawler_calls = [c for c in plan.tool_calls if c.capability == "web_crawler"]
    assert crawler_calls
    all_crawler_deps = {
        dep for c in crawler_calls for dep in c.parameters.get("depends_on", [])
    }
    assert comp_search_ids.issubset(all_crawler_deps)
    for c in crawler_calls:
        assert "urls" not in c.parameters
        assert "start_urls" not in c.parameters

    # 5. Pergunta q-sector-radar em WORKFORCE_NEEDS + cobertura das 10 seguradoras na web
    radar_questions = [q for q in plan.questions if q.id == "q-sector-radar"]
    assert len(radar_questions) == 1
    assert radar_questions[0].track == ResearchTrack.WORKFORCE_NEEDS

    for insurer in ens_cfg.ecosystem.sector_radar:
        assert f"site:{insurer.domains[0]}" in combined_google_queries, (
            f"Seguradora '{insurer.id}' ({insurer.domains[0]}) ausente do radar setorial"
        )

    # 6. Chamadas sociais ignoram handles de Instagram não confirmados
    ig_calls = [c for c in plan.tool_calls if c.capability == "instagram"]
    assert len(ig_calls) >= 1
    ig_queries = {c.query.lower().lstrip("@#") for c in ig_calls}
    assert "porto" in ig_queries or "bradescoseguros" in ig_queries
    for unconfirmed_token in ("itau", "itauseguros", "hdiseguros", "yelum", "yelumseguros", "brasilseg", "bbseguros"):
        assert unconfirmed_token not in ig_queries


def test_build_ecosystem_seed_calls_degrades_gracefully_under_tight_budget() -> None:
    ens_cfg = load_tenant_config(Path("config/tenants/ens.example.yaml"))
    understanding = CourseUnderstanding(
        analysis_id="anl-budget",
        course_title="Curso de IA para Corretores de Seguros",
        subject_domains=["seguros", "inteligência artificial"],
        geography="Brasil",
    )

    questions, calls = build_ecosystem_seed_calls(
        understanding=understanding,
        ecosystem=ens_cfg.ecosystem,
        allowed_capabilities=["google_search", "web_crawler", "instagram"],
        budget_usd=1.10,
    )

    total_allocated = sum(q.budget_allocated_usd for q in questions)
    assert total_allocated <= 1.10

    radar_google_queries = " ".join(
        c.query.lower()
        for c in calls
        if c.capability == "google_search" and c.parameters.get("ecosystem_role") == "sector_radar"
    )
    # 5 seguradoras prioritárias presentes
    for primary_domain in (
        "portoseguro.com.br",
        "bradescoseguros.com.br",
        "tokiomarine.com.br",
        "allianz.com.br",
        "hdiseguros.com.br",
    ):
        assert f"site:{primary_domain}" in radar_google_queries

    # Seguradoras secundárias omitidas sob pressão orçamentária (< US$ 1.50)
    for secondary_domain in ("mapfre.com.br", "zurich.com.br", "yelumseguros.com.br"):
        assert f"site:{secondary_domain}" not in radar_google_queries

