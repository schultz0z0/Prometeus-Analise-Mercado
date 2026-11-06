"""Testes unitários de planejamento de pesquisa clusterizado por ecossistema institucional (concorrentes fixos + radar setorial)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from prometeus.application import plan_course_research
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
        subject_domains=[
            "inteligência artificial",
            "subscrição de riscos",
            "sinistros securitários",
        ],
    )
    compact = compact_topic_terms(understanding, max_tokens=4)
    tokens = compact.split()
    assert 1 <= len(tokens) <= 4


def test_competitor_queries_preserve_course_focus_before_broadening_supporting_domains() -> None:
    cfg = load_tenant_config(Path("config/tenants/ens.example.yaml"))
    understanding = CourseUnderstanding(
        analysis_id="course-focus",
        course_title="Governança de Inteligência Artificial e Proteção de Dados no Mercado Segurador",
        subject_domains=["Inteligência artificial generativa aplicada ao mercado segurador"],
    )
    _, initial = build_ecosystem_seed_calls(understanding, cfg.ecosystem, ["google_search"], None)
    first = next(call for call in initial if call.parameters.get("competitor_id") == "fgv")
    assert "governança" in first.query
    assert "proteção" in first.query
    diagnostic = {"rows": [{"competitor_id": "fgv", "execution_status": "completed", "offers": []}]}
    second = plan_course_research.build_competitor_followup_calls(understanding, cfg.ecosystem, initial, diagnostic)
    assert "governança" in second[0].query and "dados" in second[0].query
    third = plan_course_research.build_competitor_followup_calls(understanding, cfg.ecosystem, [*initial, *second], diagnostic)
    assert "inteligência artificial" in third[0].query
    assert "governança" not in third[0].query
    assert len(second[0].query.split()) < 32


@pytest.mark.asyncio
async def test_planner_injects_individual_competitors_sector_radar_and_open_web_search() -> None:
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
                        "parameters": {
                            "priority": "critical",
                            "competitor_id": "fiap",
                            "collection_phase": "discovery",
                        },
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

    assert plan.budget_limit_usd is None
    assert plan.execution_policy is not None
    assert plan.execution_policy.spending_mode == "monitor_only"

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
        c.id for c in google_calls if c.parameters.get("ecosystem_role") == "configured_competitor"
    }
    assert len(comp_search_ids) >= 2
    individual_searches = {
        c.parameters.get("competitor_id"): c
        for c in google_calls
        if c.parameters.get("ecosystem_role") == "configured_competitor"
    }
    assert set(individual_searches) == {comp.id for comp in ens_cfg.ecosystem.competitors}
    for comp in ens_cfg.ecosystem.competitors:
        search = individual_searches[comp.id]
        assert search.parameters["collection_phase"] == "discovery"
        assert search.parameters["target_domains"] == comp.domains
        assert search.parameters["priority"] == 1
    assert plan.tool_calls[0].parameters.get("ecosystem_role") == "configured_competitor"
    untrusted_call = next(call for call in plan.tool_calls if call.id == "llm-google-site")
    assert "competitor_id" not in untrusted_call.parameters
    crawler_calls = [c for c in plan.tool_calls if c.capability == "web_crawler"]
    assert crawler_calls
    all_crawler_deps = {dep for c in crawler_calls for dep in c.parameters.get("depends_on", [])}
    assert comp_search_ids.issubset(all_crawler_deps)
    for c in crawler_calls:
        assert "urls" not in c.parameters
        assert "start_urls" not in c.parameters
        comp_id = c.parameters.get("competitor_id")
        if comp_id:
            assert c.parameters["depends_on"] == [individual_searches[comp_id].id]
            assert c.parameters["collection_phase"] == "validation"

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
    for unconfirmed_token in (
        "itau",
        "itauseguros",
        "hdiseguros",
        "yelum",
        "yelumseguros",
        "brasilseg",
        "bbseguros",
    ):
        assert unconfirmed_token not in ig_queries


def test_build_ecosystem_seed_calls_does_not_drop_sources_for_legacy_budget() -> None:
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

    # O antigo orçamento não elimina seguradoras do escopo.
    for secondary_domain in ("mapfre.com.br", "zurich.com.br", "yelumseguros.com.br"):
        assert f"site:{secondary_domain}" in radar_google_queries


def test_zero_legacy_budget_keeps_every_competitor_in_scope() -> None:
    cfg = load_tenant_config(Path("config/tenants/ens.example.yaml"))
    _, calls = build_ecosystem_seed_calls(
        understanding=CourseUnderstanding(analysis_id="no-budget-cap", course_title="Curso de IA"),
        ecosystem=cfg.ecosystem,
        allowed_capabilities=["google_search", "web_crawler"],
        budget_usd=0,
    )
    assert {
        c.parameters.get("competitor_id")
        for c in calls
        if c.capability == "google_search"
        and c.parameters.get("ecosystem_role") == "configured_competitor"
    } == {comp.id for comp in cfg.ecosystem.competitors}


def test_followup_expands_completed_low_yield_only_and_stops_after_three_variants() -> None:
    cfg = load_tenant_config(Path("config/tenants/ens.example.yaml"))
    understanding = CourseUnderstanding(
        analysis_id="expand-competitors", course_title="Governança de IA e proteção de dados",
        subject_domains=["governança de inteligência artificial", "proteção de dados"],
    )
    _, initial = build_ecosystem_seed_calls(
        understanding, cfg.ecosystem, ["google_search", "web_crawler"], None,
    )
    diagnostic = {"rows": [
        {"competitor_id": "fgv", "execution_status": "completed", "evidence_status": "no_qualified_offer", "offers": []},
        {"competitor_id": "fiap", "execution_status": "retrying", "evidence_status": "not_observed", "offers": []},
        {"competitor_id": "insper", "execution_status": "completed", "evidence_status": "direct_offer", "offers": [{"title": "Curso IA"}]},
        {"competitor_id": "alura", "execution_status": "in_doubt", "offers": []},
        {"competitor_id": "ibmec", "execution_status": "blocked", "failures": [{"error_code": "invalid_token"}], "offers": []},
    ]}
    builder = getattr(plan_course_research, "build_competitor_followup_calls", None)
    assert builder is not None, "A coleta precisa de expansão semântica determinística e limitada"
    second = builder(understanding, cfg.ecosystem, initial, diagnostic)
    assert len(second) == 2
    discovery, validation = second
    assert discovery.parameters["competitor_id"] == "fgv"
    assert discovery.parameters["semantic_variant"] == 2
    assert "site:fgv.br" in discovery.query
    assert discovery.query != next(c.query for c in initial if c.id == "eco-competitor-fgv-discovery")
    assert validation.parameters["depends_on"] == [discovery.id]
    assert validation.parameters["target_domains"] == next(
        comp.domains for comp in cfg.ecosystem.competitors if comp.id == "fgv"
    )

    third = builder(understanding, cfg.ecosystem, [*initial, *second], diagnostic)
    assert len(third) == 2
    assert third[0].parameters["semantic_variant"] == 3
    assert third[0].query != discovery.query
    assert builder(understanding, cfg.ecosystem, [*initial, *second, *third], diagnostic) == []


def test_followup_does_not_buy_validation_when_no_crawler_was_configured() -> None:
    cfg = load_tenant_config(Path("config/tenants/ens.example.yaml"))
    understanding = CourseUnderstanding(analysis_id="no-crawler", course_title="Curso de IA")
    _, initial = build_ecosystem_seed_calls(understanding, cfg.ecosystem, ["google_search"], None)
    builder = getattr(plan_course_research, "build_competitor_followup_calls", None)
    assert builder is not None
    followup = builder(understanding, cfg.ecosystem, initial, {"rows": [
        {"competitor_id": "fgv", "execution_status": "completed", "offers": []},
    ]})
    assert len(followup) == 1
    assert followup[0].capability == "google_search"
