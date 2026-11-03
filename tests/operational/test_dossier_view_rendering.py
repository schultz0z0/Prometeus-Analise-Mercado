import json
import subprocess
from pathlib import Path


def render(dossier):
    source = Path("web/js/views/dossier-view.js").resolve().as_uri()
    script = f"""import {{renderDossierView}} from {json.dumps(source)};
let input=''; for await (const chunk of process.stdin) input+=chunk;
const d=JSON.parse(input); console.log(renderDossierView({{getState:()=>({{courses:[{{id:'analysis-id',name:'MBA Seguros',dossier:d}}],activeCourseId:'analysis-id',currentDossier:d}})}}));"""
    return subprocess.run(
        ["node", "--input-type=module", "-e", script],
        input=json.dumps(dossier),
        encoding="utf-8",
        capture_output=True,
        check=True,
    ).stdout


def document():
    return {
        "status": "VERIFIED",
        "executive_summary": "Base parcial para decisão.",
        "facts_hash": "technical-hash",
        "scoring": {
            "recommendation": "INSUFFICIENT_EVIDENCE",
            "viability_score": 35.52,
            "coverage_score": 0.7,
            "confidence_score": 0.6369,
            "is_experimental": True,
            "pillar_scores": {
                "pricing": {
                    "raw_score": 0,
                    "is_present": False,
                    "missing_reason": "Sem preços comparáveis",
                }
            },
        },
        "sections": [{"title": "Diretoria", "content": "Pesquisa parcial.", "claim_ids": ["c"]}],
        "claims": [
            {
                "claim_id": "c",
                "statement": "Há lacunas de preço.",
                "verification_status": "verified",
                "evidence_ids": ["ev"],
            }
        ],
        "evidences": [
            {
                "id": "ev",
                "title": "Oferta",
                "source_name": "apify_google_search",
                "source_url": "https://example.edu/curso",
                "quality_score": 1,
            }
        ],
    }


def test_dossier_uses_statements_and_business_labels_without_engineering_metadata():
    html = render(document())
    assert "Há lacunas de preço." in html
    assert "Evidências insuficientes" in html
    assert "Precificação" in html
    assert "technical-hash" not in html
    assert "Viability Score" not in html
    assert "não informadas" not in html
    assert "Índice experimental" in html


def test_absent_pillar_has_an_explanation_instead_of_zero_performance_bar():
    html = render(document())
    assert "Sem preços comparáveis" in html
    assert "Sem amostra suficiente" in html
    assert 'aria-valuenow="0"' not in html


def test_legacy_missing_reason_is_translated_for_the_executive_view():
    doc = document()
    doc["scoring"]["pillar_scores"]["pricing"]["missing_reason"] = "Nenhuma feature verificada mínima para o pilar"
    html = render(doc)
    assert "feature" not in html
    assert "dados verificados suficientes" in html


def test_highlight_resolves_claim_and_untrusted_source_url_is_not_a_link():
    doc = document()
    doc["highlights"] = {"cons": ["c"]}
    doc["evidences"][0]["source_url"] = "javascript:alert(1)"
    html = render(doc)
    assert "Riscos e lacunas" in html
    assert 'href="javascript:' not in html
    assert "data-evidence-ids=" in html


def test_competitor_and_curriculum_tables_use_linked_claims():
    doc = document()
    doc["highlights"] = {
        "competitors": [{"label": "Escola observada", "claim_ids": ["c"]}],
        "curriculum_alignment": [
            {
                "module": "Regulação de sinistros",
                "need_claim_ids": ["c"],
                "coverage_claim_ids": ["c"],
            }
        ],
    }
    html = render(doc)
    assert "Comparação de ofertas" in html
    assert "Escola observada" in html
    assert "Regulação de sinistros" in html
    assert "Ementa e necessidades do mercado" in html


def test_new_score_blocks_and_exclusion_reasons_are_visible():
    doc=document()
    doc['scoring']['profile_id']='portfolio-v2'
    doc['scoring']['partial_score']=60
    doc['scoring']['gate_details']={'profile_id':'portfolio-v2','observed_score':60,'score_blocks':{'internal':{'score':None,'coverage':0,'confidence':0},'external':{'score':60,'coverage':0.5,'confidence':0.6}}}
    doc['analysis_audit']={'internal':{'comparables':[{'name':'MBA comparável','reason':'Mesma família','ipd_score':75}]},'pricing':{'method':'arithmetic_mean_per_comparable_course','mean_total_brl':15000,'internal_count':1,'external_count':2,'comparables':[]},'evidence':{'collected_records':3,'accepted_records':1,'context_records':1,'excluded_records':1,'used_in_score_records':1,'sources':{'apify_linkedin_jobs':{'collected_records':3,'accepted_records':1,'context_records':1,'excluded_records':1,'used_in_score_records':1,'reasons':{'Geografia incompatível':1}}}}}
    doc['evidences'][0]['sanitized_data']={'_qualification':{'accepted':False,'context_only':True,'reason':'Anúncio da própria instituição'}}
    html=render(doc)
    assert 'Score interno' in html and 'Score externo' in html
    assert 'MBA comparável' in html and 'IPD' in html
    assert 'Referência de preço' in html and '15.000' in html
    assert 'Geografia incompatível' in html
    assert 'Contexto preservado' in html
    assert 'Anúncio da própria instituição' in html
    assert 'Índice observado' in html


def test_pricing_exclusions_explain_why_an_otherwise_useful_page_is_not_a_price():
    doc = document()
    doc['analysis_audit'] = {'pricing': {
        'method': 'arithmetic_mean_per_comparable_course', 'comparables': [],
        'excluded': [{'id': 'ev', 'origin': 'external',
                      'reason_code': 'ambiguous_payment_condition'}],
    }}
    html = render(doc)
    assert 'Preços fora da referência (1)' in html
    assert 'Vários preços sem vínculo inequívoco' in html
    assert 'não exclui automaticamente a página dos outros usos' in html
    assert 'Inspecionar página' in html



def test_dossier_renders_competitive_benchmark_and_sector_radar_sections():
    doc = document()
    doc["presentation"] = {
        "competitive_benchmark": {
            "monitored_total": 10,
            "offers_found_count": 2,
            "whitespace_summary": "Apenas 2 de 10 concorrentes monitorados possuem oferta correlata; nenhum une IA generativa e regulação SUSEP.",
            "rows": [
                {
                    "competitor_id": "ibmec",
                    "name": "Ibmec",
                    "category_label": "Escola Executiva",
                    "status": "direct_offer",
                    "observed_offer_title": "MBA em Finanças, Riscos e IA",
                    "modality": "EAD Live",
                    "workload_hours": "360h",
                    "price_display": "R$ 16.800",
                    "ens_differentiation": "ENS entrega verticalização securitária e casos reais de sinistros.",
                    "evidence_ids": ["ev"],
                },
                {
                    "competitor_id": "fgv",
                    "name": "FGV Educação Executiva",
                    "category_label": "Escola Executiva",
                    "status": "no_offer_observed",
                    "observed_offer_title": "Nenhuma oferta específica observada no tema",
                    "modality": "—",
                    "workload_hours": "—",
                    "price_display": "—",
                    "ens_differentiation": "Janela de pioneirismo (whitespace) frente à FGV.",
                    "evidence_ids": [],
                },
            ],
        },
        "sector_radar": {
            "monitored_insurers_total": 10,
            "baseline_collected_at": "2026-11-03T12:00:00+00:00",
            "signals_count": 2,
            "executive_pulse": "Seguradoras líderes aceleram IA em subscrição e regulação de sinistros, exigindo reciclagem técnica de corretores.",
            "signals": [
                {
                    "actor_id": "porto-seguro",
                    "insurer_name": "Porto Seguro",
                    "priority": "primary",
                    "channel_label": "Web Institucional",
                    "scope_badge": "Brasil",
                    "theme_detected": "IA, Automação & Subscrição",
                    "market_or_broker_pain": "Automação de vistoria e cotação assistida para corretores.",
                    "curriculum_link": "Conecta-se aos módulos de subscrição e operações digitais.",
                    "source_url": "https://www.portoseguro.com.br/corretores/ia",
                    "evidence_ids": ["ev"],
                },
                {
                    "actor_id": "mapfre",
                    "insurer_name": "MAPFRE",
                    "priority": "secondary",
                    "channel_label": "LinkedIn",
                    "scope_badge": "Global (contextual)",
                    "theme_detected": "Grandes Riscos, Rural & ESG",
                    "market_or_broker_pain": "Modelagem preditiva corporativa em grandes riscos.",
                    "curriculum_link": "Referência internacional para estudos de caso.",
                    "source_url": "https://www.linkedin.com/company/mapfre/posts/1",
                    "evidence_ids": ["ev"],
                },
            ],
        },
    }
    doc["analysis_audit"] = {
        "pricing": {
            "method": "arithmetic_mean_per_comparable_course",
            "comparables": [],
            "excluded": [
                {
                    "id": "ev",
                    "origin": "external",
                    "reason_code": "sector_ecosystem_not_course_offer",
                }
            ],
        }
    }
    html = render(doc)
    assert 'id="sec-competitive-benchmark"' in html
    assert "Ibmec" in html
    assert "R$ 16.800" in html
    assert "Oferta direta" in html
    assert "Sem oferta observada" in html
    assert 'id="sec-sector-radar"' in html
    assert "Porto Seguro" in html
    assert "Global (contextual)" in html
    assert "Seguradora do Radar Setorial" in html
