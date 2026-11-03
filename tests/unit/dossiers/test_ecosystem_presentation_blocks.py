"""Testes unitários dos blocos visuais de Benchmark de Concorrência Educacional e Radar Setorial no Dossiê."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

from prometeus.application.synthesize_dossier import DossierSynthesisService
from prometeus.domain.dossiers import (
    DossierClaim,
    DossierFactItem,
    DossierFacts,
    DossierHighlights,
    DossierOutput,
)
from prometeus.infrastructure.llm.fake import FakeGenerativeModel


def test_build_visual_presentation_blocks_generates_competitive_benchmark_and_sector_radar() -> None:
    institution_ctx = {
        "id": "ens",
        "name": "Escola de Negócios e Seguros",
        "domains": ["ens.edu.br"],
        "competitors": [
            {
                "id": "ibmec",
                "name": "Ibmec",
                "category": "executive_business",
                "domains": ["ibmec.br", "pos.ibmec.br"],
                "focus_notes": "MBAs executivos em Finanças e Riscos.",
                "social": {"instagram_handle": "ibmec", "linkedin_scope": "national"},
            },
            {
                "id": "conhecer-seguros",
                "name": "Conhecer Seguros",
                "category": "direct_specialist",
                "domains": ["conhecerseguros.com.br"],
                "focus_notes": "Cursos livres técnicos de seguros.",
                "social": {"instagram_handle": "conhecerseguros", "linkedin_scope": "national"},
            },
            {
                "id": "fgv",
                "name": "FGV Educação Executiva",
                "category": "executive_business",
                "domains": ["fgv.br"],
                "focus_notes": "MBAs executivos em Seguros e Previdência.",
                "social": {"instagram_handle": "fgv.oficial", "linkedin_scope": "national"},
            },
            {
                "id": "alura",
                "name": "Alura",
                "category": "tech_edtech",
                "domains": ["alura.com.br"],
                "focus_notes": "Cursos rápidos em IA e Dados.",
                "social": {"instagram_handle": "aluraonline", "linkedin_scope": "national"},
            },
        ],
        "sector_radar": [
            {
                "id": "porto-seguro",
                "name": "Porto Seguro",
                "priority": "primary",
                "domains": ["portoseguro.com.br"],
                "monitoring_focus": ["IA e telemetria", "corretores"],
                "social": {"instagram_handle": "porto", "linkedin_scope": "national"},
            },
            {
                "id": "mapfre",
                "name": "MAPFRE",
                "priority": "secondary",
                "domains": ["mapfre.com.br"],
                "monitoring_focus": ["agronegócio", "grandes riscos"],
                "social": {"instagram_handle": "mapfrebrasil", "linkedin_scope": "global"},
            },
        ],
    }

    analysis = SimpleNamespace(
        id="anl-ens-visual",
        tenant_id="ens",
        course_name="MBA em Inteligência Artificial Aplicada a Seguros",
        proposal_data={
            "ticket": 14900.0,
            "price_period": "total",
            "workload_hours": 360,
            "modality": "EAD Live",
            "_institution_context": institution_ctx,
        },
    )
    scoring = SimpleNamespace(
        viability_score=81.5,
        confidence_score=0.86,
        recommendation="APPROVED",
    )
    facts = DossierFacts(
        analysis_id="anl-ens-visual",
        course_name="MBA em Inteligência Artificial Aplicada a Seguros",
        target_audience="Gestores e Corretores de Seguros",
        recommendation="APPROVED",
        viability_score=81.5,
        coverage_score=0.90,
        confidence_score=0.86,
        items=[
            DossierFactItem(
                evidence_id="ev-ibmec-mba",
                source_type="OFFER",
                title="MBA Executivo em Finanças, Riscos e IA — Ibmec",
                key_metrics={
                    "actor_role": "configured_competitor",
                    "matched_actor_id": "ibmec",
                    "matched_actor_name": "Ibmec",
                    "price_brl": 16800.0,
                    "workload_hours": 360,
                },
                summary="Oferta ativa EAD Live em São Paulo, Brasil.",
                source_url="https://pos.ibmec.br/mba-financas-riscos-ia",
            ),
            DossierFactItem(
                evidence_id="ev-conhecer-curto",
                source_type="OFFER",
                title="Curso Livre de IA na Subscrição de Seguros",
                key_metrics={
                    "actor_role": "configured_competitor",
                    "matched_actor_id": "conhecer-seguros",
                    "matched_actor_name": "Conhecer Seguros",
                    "price_brl": 890.0,
                    "workload_hours": 24,
                },
                summary="Curso rápido assíncrono voltado a corretores.",
                source_url="https://conhecerseguros.com.br/ia-subscricao",
            ),
            DossierFactItem(
                evidence_id="ev-porto-radar",
                source_type="OFFER",
                title="Porto Seguro automatiza vistoria e sinistros com IA generativa",
                key_metrics={
                    "evidence_role": "context_only",
                    "actor_role": "sector_radar",
                    "matched_actor_id": "porto-seguro",
                    "matched_actor_name": "Porto Seguro",
                    "linkedin_scope": "national",
                },
                summary="Corretores precisam dominar triagem assistida por IA.",
                source_url="https://www.portoseguro.com.br/corretores/ia-sinistros",
            ),
            DossierFactItem(
                evidence_id="ev-mapfre-linkedin",
                source_type="SOCIAL_VOICE",
                title="MAPFRE Global LinkedIn — Transformação Digital em Grandes Riscos",
                key_metrics={
                    "evidence_role": "context_only",
                    "actor_role": "sector_radar",
                    "matched_actor_id": "mapfre",
                    "matched_actor_name": "MAPFRE",
                    "linkedin_scope": "global",
                },
                summary="Diretrizes corporativas globais de subscrição preditiva.",
                source_url="https://www.linkedin.com/company/mapfre/posts/123",
            ),
        ],
        research_plan={
            "tool_calls": [
                {
                    "id": "eco-competitors-gsearch-1",
                    "capability": "google_search",
                    "query": "(site:ibmec.br OR site:conhecerseguros.com.br OR site:fgv.br) curso ia seguros",
                }
            ]
        },
        analysis_audit={
            "pricing": {"mean_total_brl": 16800.0},
            "sector_radar_baseline": {
                "id": "rdr-1",
                "collected_at": "2026-11-03T12:00:00+00:00",
                "signals": [],
            },
        },
    )
    dossier = DossierOutput(
        analysis_id="anl-ens-visual",
        facts_hash=facts.compute_facts_hash(),
        executive_summary="Oportunidade clara de diferenciação setorial em IA para Seguros.",
        claims=[
            DossierClaim(
                claim_id="c-1",
                statement="Há espaço para MBA verticalizado em seguros.",
                evidence_ids=["ev-ibmec-mba"],
            )
        ],
        highlights=DossierHighlights(pros=["c-1"]),
    )

    svc = DossierSynthesisService(AsyncMock(), FakeGenerativeModel())
    blocks = svc._build_visual_presentation_blocks(analysis, scoring, facts, dossier)

    assert "competitive_benchmark" in blocks
    comp_block = blocks["competitive_benchmark"]
    assert comp_block["monitored_total"] == 4
    assert comp_block["offers_found_count"] == 2
    by_comp_id = {row["competitor_id"]: row for row in comp_block["rows"]}

    assert by_comp_id["ibmec"]["status"] == "direct_offer"
    assert "16.800" in by_comp_id["ibmec"]["price_display"]
    assert by_comp_id["ibmec"]["evidence_ids"] == ["ev-ibmec-mba"]

    assert by_comp_id["conhecer-seguros"]["status"] == "adjacent_offer"
    assert by_comp_id["conhecer-seguros"]["evidence_ids"] == ["ev-conhecer-curto"]

    # FGV foi consultada na query site:fgv.br, mas sem oferta observada -> nunca inventa preço
    assert by_comp_id["fgv"]["status"] == "no_offer_observed"
    assert by_comp_id["fgv"]["price_display"] == "—"

    # Alura não constava na query executada -> not_queried
    assert by_comp_id["alura"]["status"] == "not_queried"

    assert "sector_radar" in blocks
    radar_block = blocks["sector_radar"]
    assert radar_block["monitored_insurers_total"] == 2
    assert radar_block["signals_count"] == 2
    by_actor = {sig["actor_id"]: sig for sig in radar_block["signals"]}
    assert by_actor["porto-seguro"]["scope_badge"] == "Brasil"
    assert by_actor["porto-seguro"]["evidence_ids"] == ["ev-porto-radar"]
    assert by_actor["mapfre"]["scope_badge"] == "Global (contextual)"
    assert by_actor["mapfre"]["evidence_ids"] == ["ev-mapfre-linkedin"]
