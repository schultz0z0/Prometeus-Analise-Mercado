"""Testes operacionais (Node ESM) para a interface CMS de 9 Subpáginas em Dark Theme do Dossiê Executivo."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def render_with_tab(dossier: dict, active_tab: str = "overview") -> str:
    source = Path("web/js/views/dossier-view.js").resolve().as_uri()
    script = f"""import {{renderDossierView}} from {json.dumps(source)};
let input=''; for await (const chunk of process.stdin) input+=chunk;
const payload=JSON.parse(input);
console.log(renderDossierView({{
  getState:()=>({{
    courses:[{{id:'analysis-cms-1',name:'MBA em Seguros e IA',level:'MBA',modality:'EAD Live',ticket:12900,dossier:payload.dossier}}],
    activeCourseId:'analysis-cms-1',
    currentDossier:payload.dossier,
    activeDossierTab:payload.activeTab
  }})
}}));"""
    return subprocess.run(
        ["node", "--input-type=module", "-e", script],
        input=json.dumps({"dossier": dossier, "activeTab": active_tab}),
        encoding="utf-8",
        capture_output=True,
        check=True,
    ).stdout


def sample_dossier() -> dict:
    return {
        "status": "VERIFIED",
        "executive_summary": "A combinação dos pilares resulta em viabilidade consistente para lançamento.",
        "facts_hash": "hash-cms-01",
        "scoring": {
            "recommendation": "APPROVED_WITH_ADJUSTMENTS",
            "viability_score": 78.2,
            "coverage_score": 0.88,
            "confidence_score": 0.80,
            "is_experimental": False,
            "pillar_scores": {
                "internal_history": {"raw_score": 86, "is_present": True, "confidence": 0.9},
                "paid_competition": {"raw_score": 72, "is_present": True, "confidence": 0.8},
                "search_and_media": {"raw_score": 82, "is_present": True, "confidence": 0.85},
                "employability": {"raw_score": 79, "is_present": True, "confidence": 0.8},
                "syllabus_fit": {"raw_score": 84, "is_present": True, "confidence": 0.9},
                "pricing": {"raw_score": 68, "is_present": True, "confidence": 0.75},
            },
        },
        "sections": [
            {
                "title": "Diretoria Executiva",
                "content": "Demanda aquecida com espaço claro de diferenciação.",
                "claim_ids": ["CLM-1"],
            }
        ],
        "claims": [
            {
                "claim_id": "CLM-1",
                "statement": "Foram observadas 28 vagas abertas para especialistas em IA e Seguros.",
                "verification_status": "verified",
                "support_level": "observed",
                "evidence_ids": ["ev-1"],
            }
        ],
        "evidences": [
            {
                "id": "ev-1",
                "title": "Vagas LinkedIn Seguros <script>alert(1)</script>",
                "source_name": "apify_linkedin_jobs",
                "source_url": "https://linkedin.com/jobs/view/1",
                "quality_score": 0.92,
            }
        ],
        "presentation": {
            "contract_version": 2,
            "highlights": {
                "pros": ["CLM-1"],
                "cons": [],
                "action_recommendations": [
                    {
                        "area": "marketing",
                        "action": "Priorizar captação executiva em corretoras e seguradoras.",
                        "claim_ids": ["CLM-1"],
                        "priority": "high",
                    }
                ],
                "validation_criteria": [
                    {
                        "criterion": "Validar orçamento de captação com Financeiro",
                        "target": "ROI do 1º semestre",
                        "claim_ids": ["CLM-1"],
                    }
                ],
            },
            "limitations": ["Custos fixos detalhados pendentes de homologação financeira."],
        },
    }


def test_cms_shell_renders_all_nine_tabs_breadcrumb_and_dark_theme_components() -> None:
    html = render_with_tab(sample_dossier(), "overview")

    # 9 abas canônicas na barra superior do CMS
    for tab_label in (
        "Visão Geral",
        "Métricas-Chave",
        "Concorrência Fixa",
        "Radar Setorial",
        "Economia &amp; Cenários",
        "SWOT &amp; TOWS",
        "Pilares de Viabilidade",
        "Revisões",
        "Fontes &amp; Evidências",
    ):
        assert tab_label in html

    # Breadcrumb + Cabeçalho CMS
    assert "cms-breadcrumb" in html
    assert "Dossiês" in html
    assert "MBA em Seguros e IA" in html
    assert "IVO — Índice de Viabilidade de Oferta" in html
    assert "IE — Índice de Evidência" in html
    assert "Dimensões do Score de Viabilidade" in html
    assert "Matriz de Decisão" in html

    # Gráficos SVG das subpáginas presentes e escapados contra XSS
    assert "cms-donut-svg" in html
    assert "cms-radar-svg" in html
    assert "cms-positioning-svg" in html
    assert "cms-funnel-stage" in html
    assert "<script>alert(1)</script>" not in html


def test_cms_revisions_and_sources_tabs_render_governance_and_method_pipeline() -> None:
    html_rev = render_with_tab(sample_dossier(), "revisions")
    assert 'class="cms-tab-panel is-active"\n          data-cms-panel="revisions"' in html_rev
    assert "Status de Revisão por Área" in html_rev
    assert "Status Geral da Revisão" in html_rev
    assert "Histórico de Versões" in html_rev
    assert "Comentários e Observações" in html_rev
    assert "form-cms-area-review" in html_rev

    html_src = render_with_tab(sample_dossier(), "sources_evidences")
    assert 'class="cms-tab-panel is-active"\n          data-cms-panel="sources_evidences"' in html_src
    assert "Fontes Coletadas" in html_src
    assert "Cobertura da Pesquisa" in html_src
    assert "Confiabilidade das Evidências" in html_src
    assert "Método da Análise" in html_src


def test_legacy_cms_fallback_does_not_invent_sources_themes_or_positioning():
    source = Path("web/js/views/dossier-cms-tabs.js").resolve().as_uri()
    script = f"""import {{ensureCmsPages}} from {json.dumps(source)};
let input=''; for await (const chunk of process.stdin) input+=chunk;
console.log(JSON.stringify(ensureCmsPages(JSON.parse(input), {{name:'Curso',ticket:12900}})));"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script], input=json.dumps(sample_dossier()),
        encoding="utf-8", capture_output=True, check=True,
    )
    pages = json.loads(result.stdout)["pages"]
    assert pages["sector_radar"]["subthemes_distribution"] == []
    assert all(axis.get("benchmark") is None for axis in pages["sector_radar"]["radar_axes"])
    assert pages["fixed_competition"]["positioning_map"]["points"] == []
    sources = pages["sources_evidences"]["collected_sources"]
    assert len(sources) == 1
    assert sources[0]["records_count"] == 1
    assert sources[0]["source_name"] == "apify_linkedin_jobs"
    assert pages["sector_radar"]["kpis"][1]["value"] == "Não apurada"


def test_legacy_fallback_respects_missing_scores_weights_and_real_negative_economics():
    from prometeus.application.synthesize_dossier import DossierSynthesisService
    from prometeus.domain.economics import CourseEconomicsInput

    dossier = sample_dossier()
    dossier["scoring"]["pillar_scores"] = {
        "employability": {"raw_score": 79, "is_present": True, "weight": 0.25,
                          "features": {"evidence_ids": ["one", "one", "two"]}},
    }
    dossier["presentation"]["economics"] = DossierSynthesisService._build_economics_presentation({
        "economics": CourseEconomicsInput(
            total_price_brl=1000, instruction_and_coordination_cost_brl=100000,
        ).model_dump(mode="json"),
    })
    source = Path("web/js/views/dossier-cms-tabs.js").resolve().as_uri()
    script = f"""import {{ensureCmsPages}} from {json.dumps(source)};
let input=''; for await (const chunk of process.stdin) input+=chunk;
console.log(JSON.stringify(ensureCmsPages(JSON.parse(input), {{name:'Curso',ticket:1000}})));"""
    result = subprocess.run(["node", "--input-type=module", "-e", script],
                            input=json.dumps(dossier), encoding="utf-8", capture_output=True, check=True)
    pages = json.loads(result.stdout)["pages"]
    rows = {r["key"]: r for r in pages["overview"]["decision_matrix"]}
    assert rows["employability"]["weight_pct"] == 25
    assert rows["employability"]["evidence_count"] == 2
    assert rows["internal_history"]["score"] is None
    assert pages["key_metrics"]["kpis"][2]["value"] == "Não observado"
    assert pages["sector_radar"]["attractiveness_score"] is None
    assert pages["sector_radar"]["kpis"][4]["value"] == "Não observado"
    assert pages["economics"]["status"] == "calculated"
    assert pages["economics"]["kpis"][-1]["tone"] == "risk"
    assert "-" in pages["economics"]["kpis"][-1]["value"]
    html = render_with_tab(dossier, "economics")
    expected = dossier["presentation"]["economics"]["scenarios"][1]["margin"]
    assert f'data-tone="risk">{expected}</span>' in html
    assert "Sem amostra" in html
    assert '<ellipse cx="285"' not in html
    assert "Profundidade</text>" not in html


def test_executive_svg_charts_and_horizontal_split_kpis_render_for_complete_dossier(tmp_path):
    import asyncio
    import importlib.util
    import sqlite3

    spec = importlib.util.spec_from_file_location(
        "seed_stj_showcase_dossier", Path("scripts/seed_stj_showcase_dossier.py").resolve()
    )
    assert spec and spec.loader
    seeder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seeder)

    db_file = tmp_path / "showcase.db"
    asyncio.run(seeder.seed_showcase_dossier(str(db_file)))

    conn = sqlite3.connect(str(db_file))
    row = conn.execute(
        "SELECT presentation, executive_summary, facts_hash, status FROM dossiers WHERE analysis_id = ?",
        ("anl-stj-001",),
    ).fetchone()
    conn.close()
    assert row is not None
    presentation = json.loads(row[0])

    dossier = sample_dossier()
    dossier["presentation"] = presentation
    dossier["executive_summary"] = row[1]
    dossier["facts_hash"] = row[2]
    dossier["status"] = row[3]

    html = render_with_tab(dossier, "economics")
    assert "cms-kpi-card__head" in html
    assert "cms-kpi-card__icon" in html
    assert "cms-kpi-card__metric-col" in html
    assert "cms-kpi-card__unit" in html
    assert "cms-waterfall-svg" in html
    assert "cms-trend-svg" in html
    assert "cms-trajectory-svg" in html
    assert "cms-funnel-stage" in html
    assert "cms-inst-badge" in html
    assert "cms-radar-svg" in html
    assert "cms-bubble-map-svg" in html
    assert "cms-sensitivity-table" in html

