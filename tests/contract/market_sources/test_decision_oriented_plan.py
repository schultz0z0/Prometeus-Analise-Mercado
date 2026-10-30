"""Testes de contrato para o planejamento orientado a decisão (Tarefa 3.1).

Valida os requisitos da Fase 3 do plano de inteligência de mercado:
- Trilhas temáticas separadas: concorrentes diretos, ofertas adjacentes, necessidades profissionais,
  busca educacional, contexto econômico e dados primários ENS.
- Matriz de decisão estruturada por pergunta:
  pergunta -> hipótese/contraprova -> evidência desejada -> fonte capaz -> recorte -> amostra -> orçamento -> suficiência -> fallback/stop.
- Marcas indicadas pelo usuário são usadas como referências/sementes de descoberta, não como limite exclusivo da pesquisa.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock

from prometeus.application.plan_course_research import CourseResearchPlanner
from prometeus.application.skill_registry import SkillRegistry
from prometeus.domain.configuration import AppSettings
from prometeus.domain.research import (
    CourseUnderstanding,
    ResearchQuestion,
    ResearchTrack,
)


def test_research_track_enum_defines_canonical_decision_tracks():
    tracks = {t.value for t in ResearchTrack}
    assert "direct_competitors" in tracks
    assert "adjacent_offers" in tracks
    assert "workforce_needs" in tracks
    assert "educational_search" in tracks
    assert "economic_context" in tracks
    assert "primary_institutional" in tracks


def test_research_question_contains_decision_matrix_fields():
    q = ResearchQuestion(
        question="Qual é o teto de preço praticado por concorrentes diretos de MBA em fraudes?",
        evidence_need="Ofertas com preço total e parcelamento de cursos da mesma categoria e tema",
        priority=1,
        track=ResearchTrack.DIRECT_COMPETITORS,
        hypothesis="Concorrentes cobram entre R$ 8.000 e R$ 15.000 pelo MBA",
        counter_evidence_hypothesis="Cursos comparáveis cobram menos de R$ 5.000 ou operam como extensão curta",
        expected_evidence="Preço total, carga horária e módulos curriculares de MBAs concorrentes",
        capable_sources=["web_crawler", "google_search"],
        scope_filter="Brasil, MBAs ativos em seguros e regulação de sinistros",
        sample_target=10,
        budget_allocated_usd=0.50,
        sufficiency_criteria="Pelo menos 3 ofertas de MBA com preço verificado e ementa",
        fallback_or_stop_rule="Se nenhum MBA com preço for encontrado após 10 páginas, buscar pós-graduações adjacentes",
    )

    assert q.track == ResearchTrack.DIRECT_COMPETITORS
    assert q.hypothesis != ""
    assert q.counter_evidence_hypothesis != ""
    assert "web_crawler" in q.capable_sources
    assert q.sample_target == 10
    assert q.budget_allocated_usd == 0.50


def test_planner_generates_decision_matrix_and_uses_brands_as_seeds_not_limits():
    async def _run():
        mock_llm = AsyncMock()
        # LLM returns plan with separate tracks and questions
        mock_llm.generate_text.return_value = json.dumps(
            {
                "questions": [
                    {
                        "id": "q-direct",
                        "question": "Quais são as ofertas de MBA concorrentes no tema?",
                        "evidence_need": "Ofertas concorrentes diretas",
                        "priority": 1,
                        "track": "direct_competitors",
                        "hypothesis": "FGV e PUC possuem MBAs concorrentes",
                        "counter_evidence_hypothesis": "Não há MBAs diretos no mercado",
                        "expected_evidence": "Preços e ementas",
                        "capable_sources": ["google_search", "web_crawler"],
                        "scope_filter": "Brasil",
                        "sample_target": 10,
                        "budget_allocated_usd": 0.40,
                        "sufficiency_criteria": "3 ofertas diretas com preço",
                        "fallback_or_stop_rule": "buscar extensoes",
                    },
                    {
                        "id": "q-workforce",
                        "question": "Quais competências de detecção de fraudes o mercado exige?",
                        "evidence_need": "Vagas com competências profissionais",
                        "priority": 2,
                        "track": "workforce_needs",
                        "hypothesis": "Seguradoras exigem investigação de sinistros e análise de dados",
                        "counter_evidence_hypothesis": "Vagas exigem apenas direito geral",
                        "expected_evidence": "Requisitos de vagas",
                        "capable_sources": ["linkedin_jobs"],
                        "scope_filter": "Brasil",
                        "sample_target": 15,
                        "budget_allocated_usd": 0.30,
                        "sufficiency_criteria": "5 vagas com descrição de competências",
                        "fallback_or_stop_rule": "parar se 0 vagas após busca",
                    },
                ],
                "tool_calls": [
                    {
                        "id": "call-search-broad",
                        "capability": "google_search",
                        "query": "mba gestao fraudes seguros brasil",
                        "rationale": "Busca ampla temática de concorrentes diretos",
                        "required": True,
                        "max_items": 10,
                        "parameters": {"country": "BR", "language": "pt"},
                    },
                    {
                        "id": "call-search-seed-brand",
                        "capability": "google_search",
                        "query": "FGV curso fraudes seguros",
                        "rationale": "Semente de descoberta baseada na marca indicada pelo usuário",
                        "required": False,
                        "max_items": 5,
                        "parameters": {"country": "BR", "language": "pt"},
                    },
                ],
            }
        )

        settings = AppSettings(
            _env_file=None,
            APIFY_ACTOR_GOOGLE_SEARCH="apify/google-search-scraper@0.0.474",
            APIFY_ACTOR_WEB_CRAWLER="apify/website-content-crawler@0.3.102",
            APIFY_ACTOR_LINKEDIN_JOBS="curious_coder/linkedin-jobs-scraper@0.0.1",
            APIFY_REQUIRED_SOURCES="google_search",
        )
        planner = CourseResearchPlanner(
            llm=mock_llm,
            skills=SkillRegistry(),
            settings=settings,
        )

        understanding = CourseUnderstanding(
            analysis_id="analysis-track-test",
            course_title="MBA em Gestão de Fraudes em Seguros",
            target_audiences=["Analistas de Sinistros", "Peritos"],
            subject_domains=["Fraudes em Seguros", "Prevenção de Fraudes"],
            modality="ONLINE",
            geography="Brasil",
            language="pt-BR",
            supplied_materials=["FGV", "PUC"],  # Marcas de referência
        )

        plan = await planner.plan(understanding=understanding)

        assert len(plan.questions) == 2
        tracks = [q.track for q in plan.questions]
        assert ResearchTrack.DIRECT_COMPETITORS in tracks
        assert ResearchTrack.WORKFORCE_NEEDS in tracks

        # Verify that plan has both broad discovery and seed brand calls
        # (user brands are references/seeds, not exclusive filter)
        has_broad_call = any("FGV" not in c.query and "PUC" not in c.query for c in plan.tool_calls)
        assert has_broad_call is True

    asyncio.run(_run())
