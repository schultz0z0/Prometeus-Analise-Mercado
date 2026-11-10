"""Construtor determinístico do template CMS de 9 subpáginas do Dossiê Executivo.

Monta o contrato estruturado `cms_pages` combinando:
1. Cálculos determinísticos em código (IVO, IE, Matriz Peso x Nota, Cascata Financeira, Cenários);
2. Dados observados com rastreabilidade (`evidence_ids`, Concorrência Fixa, Radar Setorial, Fontes);
3. Sínteses narradas validadas pelo `DossierVerifier` (`claim_ids`, SWOT/TOWS, Insights, Ações).
"""

from __future__ import annotations

from typing import Any

from prometeus.domain.dossiers import DossierFacts, DossierOutput

CMS_TAB_ORDER: tuple[str, ...] = (
    "overview",
    "key_metrics",
    "fixed_competition",
    "sector_radar",
    "economics",
    "swot_tows",
    "viability_pillars",
    "revisions",
    "sources_evidences",
)

CMS_TABS_METADATA: list[dict[str, str]] = [
    {
        "id": "overview",
        "label": "Visão Geral",
        "title": "Dossiê de Viabilidade",
        "subtitle": "Relatório pós-análise de viabilidade para o lançamento do curso, com consolidação de evidências, projeções e recomendação executiva.",
        "icon": "file-text",
    },
    {
        "id": "key_metrics",
        "label": "Métricas-Chave",
        "title": "Métricas-Chave",
        "subtitle": "Consolida os principais indicadores da viabilidade, com desempenho histórico, procura externa, conversão, eficiência e resultado esperado.",
        "icon": "bar-chart-2",
    },
    {
        "id": "fixed_competition",
        "label": "Concorrência Fixa",
        "title": "Concorrência Fixa",
        "subtitle": "Monitoramento comparativo dos players educacionais monitorados e suas ofertas, com análise de posicionamento, atributos, preços e diferenciais.",
        "icon": "layers",
    },
    {
        "id": "sector_radar",
        "label": "Radar Setorial",
        "title": "Radar Setorial",
        "subtitle": "Mapeamento de tendências do setor segurador, comportamento de demanda e maturidade temática, com foco em oportunidades para o curso.",
        "icon": "compass",
    },
    {
        "id": "economics",
        "label": "Economia & Cenários",
        "title": "Economia & Cenários",
        "subtitle": "Projeções financeiras e cenários de lançamento do curso, com modelagem determinística de receita, custos, ponto de equilíbrio e sensibilidade.",
        "icon": "dollar-sign",
    },
    {
        "id": "swot_tows",
        "label": "SWOT & TOWS",
        "title": "SWOT & TOWS",
        "subtitle": "Análise do ambiente interno e externo e implicações estratégicas para o posicionamento e lançamento do curso.",
        "icon": "target",
    },
    {
        "id": "viability_pillars",
        "label": "Pilares de Viabilidade",
        "title": "Pilares de Viabilidade",
        "subtitle": "Fundamentos analíticos que estruturam a recomendação de lançamento, integrando histórico institucional, concorrência, busca, empregabilidade, ementa e preço.",
        "icon": "award",
    },
    {
        "id": "revisions",
        "label": "Revisões",
        "title": "Revisões",
        "subtitle": "Histórico de versões, comentários e aprovações por área do dossiê, garantindo rastreabilidade e governança da análise.",
        "icon": "git-commit",
    },
    {
        "id": "sources_evidences",
        "label": "Fontes & Evidências",
        "title": "Fontes & Evidências",
        "subtitle": "Rastreabilidade metodológica das informações coletadas, evidências utilizadas e bases de suporte à análise de viabilidade.",
        "icon": "database",
    },
]

OFFICIAL_PILLARS_SPEC: list[dict[str, Any]] = [
    {
        "key": "internal_history",
        "label": "Histórico Institucional",
        "short_label": "Histórico ENS",
        "decision_label": "Aderência Histórica & Portfólio",
        "weight_pct": 20,
        "icon": "building",
    },
    {
        "key": "paid_competition",
        "label": "Concorrência Paga",
        "short_label": "Oportunidade Competitiva",
        "decision_label": "Atração & Espaço Competitivo",
        "weight_pct": 20,
        "icon": "award",
    },
    {
        "key": "search_and_media",
        "label": "Busca & Mídia",
        "short_label": "Busca e Intenção",
        "decision_label": "Potencial de Demanda Externa",
        "weight_pct": 20,
        "icon": "search",
    },
    {
        "key": "employability",
        "label": "Empregabilidade",
        "short_label": "Demanda Profissional",
        "decision_label": "Absorção & Mercado de Trabalho",
        "weight_pct": 15,
        "icon": "briefcase",
    },
    {
        "key": "syllabus_fit",
        "label": "Aderência de Ementa",
        "short_label": "Aderência Estratégica",
        "decision_label": "Aderência Curricular & Ementa",
        "weight_pct": 15,
        "icon": "target",
    },
    {
        "key": "pricing",
        "label": "Precificação",
        "short_label": "Viabilidade de Preço",
        "decision_label": "Competitividade de Ticket",
        "weight_pct": 10,
        "icon": "dollar-sign",
    },
]

RECOMMENDATION_LABELS: dict[str, dict[str, str]] = {
    "APPROVED": {
        "label": "Recomendado para lançamento",
        "short_label": "Lançamento recomendado",
        "tone": "approved",
        "approval_label": "Sim",
        "approval_note": "Fundamentos e evidências sustentam avanço para homologação executiva.",
    },
    "APPROVED_WITH_ADJUSTMENTS": {
        "label": "Recomendado com ajustes",
        "short_label": "Validar com ajustes",
        "tone": "adjustments",
        "approval_label": "Com ajustes",
        "approval_note": "Avançar condicionando o lançamento à conclusão das validações recomendadas.",
    },
    "REQUIRES_HUMAN_REVIEW": {
        "label": "Requer revisão humana",
        "short_label": "Em revisão técnica",
        "tone": "running",
        "approval_label": "Em revisão",
        "approval_note": "Necessária deliberação colegiada das áreas antes da decisão final.",
    },
    "INSUFFICIENT_EVIDENCE": {
        "label": "Evidências insuficientes",
        "short_label": "Base insuficiente",
        "tone": "insufficient",
        "approval_label": "Pendente",
        "approval_note": "Ampliar coleta de evidências e premissas antes de deliberar lançamento.",
    },
    "HIGH_RISK": {
        "label": "Alto risco identificado",
        "short_label": "Alto risco",
        "tone": "risk",
        "approval_label": "Não recomendado",
        "approval_note": "Riscos competitivos ou financeiros superam os sinais favoráveis atuais.",
    },
}


def _format_brl(value: float | int | None) -> str:
    if value is None or isinstance(value, bool):
        return "—"
    num = float(value)
    if num <= 0:
        return "—"
    return f"R$ {num:,.0f}".replace(",", ".")


def _score_band(score: float, is_present: bool = True) -> dict[str, str]:
    if not is_present:
        return {"label": "Sem dados", "tone": "insufficient"}
    if score >= 75.0:
        return {"label": "Forte", "tone": "approved"}
    if score >= 55.0:
        return {"label": "Adequado", "tone": "adjustments"}
    return {"label": "Atenção", "tone": "risk"}


def _pillar_score_and_presence(facts: DossierFacts, key: str) -> tuple[float, bool, int]:
    raw_summary = facts.pillar_summaries.get(key)
    detail = facts.pillar_details.get(key) if isinstance(facts.pillar_details, dict) else None
    is_present = True
    evidence_count = 0
    if isinstance(detail, dict):
        if "is_present" in detail:
            is_present = bool(detail.get("is_present"))
        if isinstance(detail.get("evidence_count"), int):
            evidence_count = int(detail["evidence_count"])
        if raw_summary is None and isinstance(detail.get("raw_score"), (int, float)):
            raw_summary = float(detail["raw_score"])
    if raw_summary is None:
        return 0.0, False, evidence_count
    score_val = round(float(raw_summary), 1)
    return score_val, is_present, evidence_count


def _claims_map(dossier: DossierOutput) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for c in dossier.claims:
        result[c.claim_id] = {
            "claim_id": c.claim_id,
            "statement": c.statement,
            "evidence_ids": list(c.evidence_ids or []),
            "support_level": str(c.support_level.value if hasattr(c.support_level, "value") else c.support_level),
        }
    return result


def _resolve_claim_items(
    claim_ids: list[str],
    claims_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    seen: set[str] = set()
    for cid in claim_ids:
        if cid in seen:
            continue
        seen.add(cid)
        claim = claims_by_id.get(cid)
        if claim:
            resolved.append(claim)
    return resolved


def build_cms_dossier_pages(
    proposal: dict[str, Any],
    facts: DossierFacts,
    dossier: DossierOutput,
    economics: dict[str, Any],
    ecosystem: dict[str, Any],
) -> dict[str, Any]:
    """Constrói o envelope determinístico `cms_pages` com as 9 subpáginas do Dossiê Executivo."""
    ivo_score = round(float(facts.viability_score))
    coverage_pct = round(float(facts.coverage_score) * 100)
    confidence_pct = round(float(facts.confidence_score) * 100)
    ie_score = round(((float(facts.coverage_score) + float(facts.confidence_score)) / 2.0) * 100)
    rec_meta = RECOMMENDATION_LABELS.get(
        facts.recommendation,
        {
            "label": facts.recommendation or "Em avaliação",
            "short_label": facts.recommendation or "Em avaliação",
            "tone": "insufficient",
            "approval_label": "Em análise",
            "approval_note": "Parecer em consolidação.",
        },
    )
    claims_by_id = _claims_map(dossier)

    # Pillar rows used across Overview & Viability Pillars
    pillar_rows: list[dict[str, Any]] = []
    for spec in OFFICIAL_PILLARS_SPEC:
        score_val, is_present, ev_count = _pillar_score_and_presence(facts, spec["key"])
        band = _score_band(score_val, is_present)
        contribution = round((score_val * spec["weight_pct"]) / 100.0, 1) if is_present else 0.0
        pillar_rows.append(
            {
                "key": spec["key"],
                "label": spec["label"],
                "short_label": spec["short_label"],
                "decision_label": spec["decision_label"],
                "icon": spec["icon"],
                "weight_pct": spec["weight_pct"],
                "score": round(score_val),
                "raw_score": score_val,
                "is_present": is_present,
                "evidence_count": ev_count,
                "contribution_pts": contribution,
                "status_label": band["label"],
                "status_tone": band["tone"],
            }
        )

    overview_page = _build_overview_page(
        facts=facts,
        dossier=dossier,
        economics=economics,
        ivo_score=ivo_score,
        ie_score=ie_score,
        coverage_pct=coverage_pct,
        confidence_pct=confidence_pct,
        rec_meta=rec_meta,
        pillar_rows=pillar_rows,
        claims_by_id=claims_by_id,
    )
    key_metrics_page = _build_key_metrics_page(
        proposal=proposal,
        facts=facts,
        dossier=dossier,
        economics=economics,
        ecosystem=ecosystem,
        ivo_score=ivo_score,
        ie_score=ie_score,
        pillar_rows=pillar_rows,
        claims_by_id=claims_by_id,
    )
    fixed_competition_page = _build_fixed_competition_page(
        proposal=proposal,
        facts=facts,
        dossier=dossier,
        ecosystem=ecosystem,
        pillar_rows=pillar_rows,
        claims_by_id=claims_by_id,
    )
    sector_radar_page = _build_sector_radar_page(
        facts=facts,
        dossier=dossier,
        ecosystem=ecosystem,
        pillar_rows=pillar_rows,
        claims_by_id=claims_by_id,
    )
    economics_page = _build_economics_page(
        proposal=proposal,
        facts=facts,
        dossier=dossier,
        economics=economics,
        claims_by_id=claims_by_id,
    )
    swot_tows_page = _build_swot_tows_page(
        facts=facts,
        dossier=dossier,
        pillar_rows=pillar_rows,
        rec_meta=rec_meta,
        claims_by_id=claims_by_id,
    )
    viability_pillars_page = _build_viability_pillars_page(
        facts=facts,
        dossier=dossier,
        economics=economics,
        ecosystem=ecosystem,
        ivo_score=ivo_score,
        coverage_pct=coverage_pct,
        confidence_pct=confidence_pct,
        rec_meta=rec_meta,
        pillar_rows=pillar_rows,
    )
    revisions_page = _build_revisions_page(
        facts=facts,
        dossier=dossier,
        rec_meta=rec_meta,
        claims_by_id=claims_by_id,
    )
    sources_evidences_page = _build_sources_evidences_page(
        facts=facts,
        dossier=dossier,
        ecosystem=ecosystem,
        coverage_pct=coverage_pct,
        confidence_pct=confidence_pct,
        ie_score=ie_score,
        pillar_rows=pillar_rows,
    )

    return {
        "schema_version": 1,
        "default_tab": "overview",
        "course_name": facts.course_name,
        "target_audience": facts.target_audience,
        "status_badge": {
            "label": "Pós-análise concluída",
            "tone": "approved" if facts.recommendation in {"APPROVED", "APPROVED_WITH_ADJUSTMENTS"} else rec_meta["tone"],
        },
        "tabs": CMS_TABS_METADATA,
        "pages": {
            "overview": overview_page,
            "key_metrics": key_metrics_page,
            "fixed_competition": fixed_competition_page,
            "sector_radar": sector_radar_page,
            "economics": economics_page,
            "swot_tows": swot_tows_page,
            "viability_pillars": viability_pillars_page,
            "revisions": revisions_page,
            "sources_evidences": sources_evidences_page,
        },
    }


def _build_overview_page(
    *,
    facts: DossierFacts,
    dossier: DossierOutput,
    economics: dict[str, Any],
    ivo_score: int,
    ie_score: int,
    coverage_pct: int,
    confidence_pct: int,
    rec_meta: dict[str, str],
    pillar_rows: list[dict[str, Any]],
    claims_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    econ_calculated = economics.get("status") == "calculated"
    scenarios = economics.get("scenarios") if isinstance(economics.get("scenarios"), list) else []

    if econ_calculated and scenarios:
        students_vals = [int(s.get("students", 0)) for s in scenarios if isinstance(s, dict) and s.get("students")]
        min_st = min(students_vals) if students_vals else 0
        max_st = max(students_vals) if students_vals else 0
        enroll_value = f"{min_st} a {max_st}" if min_st and max_st else str(economics.get("break_even_students") or "—")
        enroll_sub = f"Equilíbrio: {economics.get('break_even_students', '—')} matrículas"
        base_scen = next((s for s in scenarios if isinstance(s, dict) and "base" in str(s.get("name", "")).lower()), scenarios[0])
        margin_value = str(base_scen.get("margin") or "—")
        margin_sub = "Cenário base simulado"
    else:
        internal_audit = facts.analysis_audit.get("internal_audit") if isinstance(facts.analysis_audit, dict) else {}
        mean_students = internal_audit.get("mean_students") if isinstance(internal_audit, dict) else None
        if isinstance(mean_students, (int, float)) and mean_students > 0:
            enroll_value = f"~{round(float(mean_students))} alunos"
            enroll_sub = "Média histórica ENS (turmas comparáveis)"
        else:
            enroll_value = "Requer premissas"
            enroll_sub = "Informe capacidade e custos da turma"
        margin_value = "Requer premissas"
        margin_sub = "Informe custos fixos e variáveis para simular"

    ivo_delta = ivo_score - 75
    ivo_delta_label = f"{'+' if ivo_delta >= 0 else ''}{ivo_delta} pts vs. limiar favorável (75)"

    scenario_cards: list[dict[str, Any]] = []
    if econ_calculated and scenarios:
        labels = ["Conservador", "Base", "Otimista"]
        for idx, scen in enumerate(scenarios[:3]):
            if not isinstance(scen, dict):
                continue
            label = labels[idx] if idx < len(labels) else str(scen.get("name") or f"Cenário {idx + 1}")
            scenario_cards.append(
                {
                    "name": label,
                    "is_reference": idx == 1,
                    "students_label": str(scen.get("students", "—")),
                    "revenue_label": _format_brl(float(scen["net_revenue"])) if scen.get("net_revenue") is not None else "—",
                    "margin_label": str(scen.get("margin") or "—"),
                    "result_label": _format_brl(float(scen["net_result"])) if scen.get("net_result") is not None else "—",
                }
            )
    else:
        for idx, label in enumerate(("Conservador", "Base", "Otimista")):
            scenario_cards.append(
                {
                    "name": label,
                    "is_reference": idx == 1,
                    "students_label": "Requer premissas",
                    "revenue_label": "Requer premissas",
                    "margin_label": "Requer premissas",
                    "result_label": "Simulação pendente",
                }
            )

    insight_ids = list(dossier.highlights.pros) + list(dossier.executive_summary_claim_ids)
    insights = _resolve_claim_items(insight_ids, claims_by_id)
    if not insights and dossier.claims:
        insights = _resolve_claim_items([c.claim_id for c in dossier.claims[:5]], claims_by_id)

    return {
        "ivo_score": ivo_score,
        "ie_score": ie_score,
        "coverage_pct": coverage_pct,
        "confidence_pct": confidence_pct,
        "recommendation_code": facts.recommendation,
        "recommendation_label": rec_meta["short_label"],
        "recommendation_tone": rec_meta["tone"],
        "kpis": [
            {
                "id": "ivo",
                "title": "IVO — Índice de Viabilidade de Oferta",
                "value": f"{ivo_score}/100",
                "badge": ivo_delta_label,
                "tone": "approved" if ivo_score >= 75 else ("adjustments" if ivo_score >= 55 else "risk"),
                "sublabel": "Escala 0–100 calculada sobre 6 pilares",
            },
            {
                "id": "ie",
                "title": "IE — Índice de Evidência",
                "value": f"{ie_score}/100",
                "badge": f"Cobertura {coverage_pct}% · Confiança {confidence_pct}%",
                "tone": "approved" if ie_score >= 75 else "adjustments",
                "sublabel": "Suporte empírico e rastreabilidade",
            },
            {
                "id": "recommendation",
                "title": "Recomendação",
                "value": rec_meta["short_label"],
                "badge": rec_meta["label"],
                "tone": rec_meta["tone"],
                "sublabel": "Parecer determinístico da matriz",
            },
            {
                "id": "enrollment",
                "title": "Referência de Matrículas",
                "value": enroll_value,
                "badge": "Simulado" if econ_calculated else "Histórico / Premissa",
                "tone": "running" if econ_calculated else "insufficient",
                "sublabel": enroll_sub,
            },
            {
                "id": "margin",
                "title": "Margem Prevista",
                "value": margin_value,
                "badge": "Cenário Base" if econ_calculated else "Pendente",
                "tone": "approved" if econ_calculated else "insufficient",
                "sublabel": margin_sub,
            },
        ],
        "dimensions_bars": pillar_rows,
        "scenario_summary": {
            "status": "calculated" if econ_calculated else "assumptions_required",
            "cards": scenario_cards,
        },
        "decision_matrix": pillar_rows,
        "key_insights": insights[:5],
        "executive_summary": dossier.executive_summary,
    }


def _build_key_metrics_page(
    *,
    proposal: dict[str, Any],
    facts: DossierFacts,
    dossier: DossierOutput,
    economics: dict[str, Any],
    ecosystem: dict[str, Any],
    ivo_score: int,
    ie_score: int,
    pillar_rows: list[dict[str, Any]],
    claims_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    internal_audit = facts.analysis_audit.get("internal_audit") if isinstance(facts.analysis_audit, dict) else {}
    internal_audit = internal_audit if isinstance(internal_audit, dict) else {}
    pricing_audit = facts.analysis_audit.get("pricing") if isinstance(facts.analysis_audit, dict) else {}
    pricing_audit = pricing_audit if isinstance(pricing_audit, dict) else {}

    mean_students = internal_audit.get("mean_students")
    mean_evasion = internal_audit.get("mean_evasion_rate")
    retention_pct = round((1.0 - float(mean_evasion)) * 100, 1) if isinstance(mean_evasion, (int, float)) else None
    internal_score = next((p["score"] for p in pillar_rows if p["key"] == "internal_history"), 0)
    search_score = next((p["score"] for p in pillar_rows if p["key"] == "search_and_media"), 0)

    proposed_ticket = proposal.get("ticket")
    market_mean_ticket = pricing_audit.get("mean_total_brl")
    econ_calculated = economics.get("status") == "calculated"
    var_cost = economics.get("variable_cost_per_student") if econ_calculated else None
    scenarios = economics.get("scenarios") if isinstance(economics.get("scenarios"), list) else []
    base_margin = scenarios[1].get("margin") if econ_calculated and len(scenarios) > 1 and isinstance(scenarios[1], dict) else None

    comparables = internal_audit.get("comparables") if isinstance(internal_audit.get("comparables"), list) else []
    historical_series: list[dict[str, Any]] = []
    for idx, comp in enumerate(comparables[:6]):
        if not isinstance(comp, dict):
            continue
        st_count = int(comp.get("students_count") or 0)
        ev_rate = float(comp.get("evasion_rate") or 0.0)
        retained = max(0, round(st_count * (1.0 - ev_rate)))
        historical_series.append(
            {
                "label": str(comp.get("course_name") or f"Turma {idx + 1}")[:28],
                "students": st_count,
                "retained": retained,
                "retention_pct": round((1.0 - ev_rate) * 100, 1),
            }
        )

    max_cap = int(economics.get("max_capacity") or proposal.get("max_capacity") or 0)
    be_students = int(economics.get("break_even_students") or 0) if econ_calculated else 0
    hist_avg_int = round(float(mean_students)) if isinstance(mean_students, (int, float)) and mean_students > 0 else 0

    funnel_stages = [
        {
            "stage": "Capacidade / Referência",
            "value_label": f"{max_cap} vagas" if max_cap > 0 else (f"{hist_avg_int} alunos (hist.)" if hist_avg_int > 0 else "Requer premissa"),
            "pct_label": "100%",
            "width_pct": 100,
        },
        {
            "stage": "Média Histórica ENS",
            "value_label": f"{hist_avg_int} matriculados" if hist_avg_int > 0 else "Sem comparáveis",
            "pct_label": f"{internal_score}% aderência" if internal_score else "—",
            "width_pct": 80,
        },
        {
            "stage": "Retenção Estimada (Hist.)",
            "value_label": f"{round(hist_avg_int * (retention_pct / 100.0))} concluintes" if hist_avg_int and retention_pct else "Não observado",
            "pct_label": f"{retention_pct}%" if retention_pct is not None else "—",
            "width_pct": 62,
        },
        {
            "stage": "Ponto de Equilíbrio",
            "value_label": f"{be_students} matrículas" if be_students > 0 else "Requer custos",
            "pct_label": "Breakeven" if be_students > 0 else "Pendente",
            "width_pct": 46,
        },
    ]

    comp_bench = ecosystem.get("competitive_benchmark") if isinstance(ecosystem.get("competitive_benchmark"), dict) else {}
    offers_found = comp_bench.get("offers_found_count", 0)
    monitored_total = comp_bench.get("monitored_total", 0)

    dimension_indicators = [
        {
            "dimension": "Demanda & Mídia",
            "indicator": "Score de Busca e Mídia",
            "observed": f"{search_score}/100",
            "reference": "≥ 70/100",
            "delta": f"{search_score - 70:+d} pts",
            "status": "Forte" if search_score >= 75 else ("Adequada" if search_score >= 55 else "Atenção"),
        },
        {
            "dimension": "Oferta Competitiva",
            "indicator": "Concorrentes com oferta direta",
            "observed": f"{offers_found} de {monitored_total}" if monitored_total else "—",
            "reference": f"{monitored_total} monitorados" if monitored_total else "Catálogo IES",
            "delta": f"{monitored_total - offers_found} sem oferta" if monitored_total else "—",
            "status": "Favorável" if offers_found <= max(1, monitored_total // 2) else "Competitivo",
        },
        {
            "dimension": "Aderência ENS",
            "indicator": "Compatibilidade histórica",
            "observed": f"{internal_score}%",
            "reference": "≥ 75%",
            "delta": f"{internal_score - 75:+d} p.p.",
            "status": "Forte" if internal_score >= 75 else "Adequada",
        },
        {
            "dimension": "Retenção Histórica",
            "indicator": "Taxa média de retenção ENS",
            "observed": f"{retention_pct}%" if retention_pct is not None else "Não observado",
            "reference": "≥ 85%",
            "delta": f"{round(retention_pct - 85, 1):+.1f} p.p." if retention_pct is not None else "—",
            "status": "Forte" if (retention_pct or 0) >= 85 else "Adequada",
        },
        {
            "dimension": "Viabilidade Global",
            "indicator": "IE / IVO consolidado",
            "observed": f"IE {ie_score} · IVO {ivo_score}",
            "reference": "≥ 75/100",
            "delta": f"{ivo_score - 75:+d} pts IVO",
            "status": "Forte" if ivo_score >= 75 else "Adequada",
        },
    ]

    internal_benchmark = [
        {
            "indicator": "Alunos por turma (média)",
            "ens_reference": f"{hist_avg_int} alunos" if hist_avg_int else "Não informado",
            "proposed_course": f"{be_students} (equilíbrio)" if be_students else "Requer premissas",
            "delta": f"{len(comparables)} comparáveis" if comparables else "—",
        },
        {
            "indicator": "Taxa de retenção (1 - evasão)",
            "ens_reference": f"{retention_pct}%" if retention_pct is not None else "Não informado",
            "proposed_course": "Meta ≥ 90%",
            "delta": f"Evasão hist. {round(float(mean_evasion) * 100, 1)}%" if isinstance(mean_evasion, (int, float)) else "—",
        },
        {
            "indicator": "Ticket total de referência",
            "ens_reference": _format_brl(market_mean_ticket) if isinstance(market_mean_ticket, (int, float)) else "Sem média de mercado",
            "proposed_course": _format_brl(proposed_ticket) if isinstance(proposed_ticket, (int, float)) else "Não declarado",
            "delta": (
                f"{round(((float(proposed_ticket) - float(market_mean_ticket)) / float(market_mean_ticket)) * 100, 1):+.1f}% vs. mercado"
                if isinstance(proposed_ticket, (int, float)) and isinstance(market_mean_ticket, (int, float)) and float(market_mean_ticket) > 0
                else "—"
            ),
        },
        {
            "indicator": "Índices IE / IVO",
            "ens_reference": "Limiar 75/100",
            "proposed_course": f"IE {ie_score}/100 · IVO {ivo_score}/100",
            "delta": f"{ivo_score - 75:+d} pts vs. limiar",
        },
    ]

    highlights = _resolve_claim_items([c.claim_id for c in dossier.claims[:6]], claims_by_id)

    return {
        "kpis": [
            {
                "id": "hist_students",
                "title": "Alunos Históricos (Média ENS)",
                "value": f"{hist_avg_int} alunos" if hist_avg_int else "Não observado",
                "badge": f"{len(comparables)} turmas comparáveis" if comparables else "Sem base histórica",
                "tone": "approved" if hist_avg_int else "insufficient",
                "sublabel": "Portfólio histórico da instituição",
            },
            {
                "id": "hist_retention",
                "title": "Retenção Histórica ENS",
                "value": f"{retention_pct}%" if retention_pct is not None else "Não observado",
                "badge": f"Evasão média {round(float(mean_evasion) * 100, 1)}%" if isinstance(mean_evasion, (int, float)) else "Requer histórico",
                "tone": "approved" if (retention_pct or 0) >= 85 else "adjustments",
                "sublabel": "Taxa de conclusão observada na ENS",
            },
            {
                "id": "ens_fit",
                "title": "Aderência da Base ENS",
                "value": f"{internal_score}%",
                "badge": "Pilar Histórico",
                "tone": "approved" if internal_score >= 75 else "adjustments",
                "sublabel": "Alinhamento ao histórico institucional",
            },
            {
                "id": "external_demand",
                "title": "Procura Externa (Busca & Mídia)",
                "value": f"{search_score}/100",
                "badge": "Sinais externos",
                "tone": "approved" if search_score >= 75 else "adjustments",
                "sublabel": "Score consolidado de busca e mídia",
            },
            {
                "id": "ticket_projected",
                "title": "Ticket Médio Projetado",
                "value": _format_brl(proposed_ticket) if isinstance(proposed_ticket, (int, float)) else "Não declarado",
                "badge": f"Mercado: {_format_brl(market_mean_ticket)}" if isinstance(market_mean_ticket, (int, float)) else "Sem benchmark de preço",
                "tone": "running" if isinstance(proposed_ticket, (int, float)) else "insufficient",
                "sublabel": "Valor declarado na proposta do curso",
            },
            {
                "id": "variable_cost",
                "title": "Custo Variável / Aluno",
                "value": _format_brl(float(var_cost)) if var_cost is not None else "Requer premissa",
                "badge": "Simulado" if var_cost is not None else "Premissa financeira",
                "tone": "running" if var_cost is not None else "insufficient",
                "sublabel": "Custo variável efetivo por matrícula",
            },
            {
                "id": "margin_expected",
                "title": "Margem Prevista",
                "value": str(base_margin) if base_margin else "Requer premissa",
                "badge": "Cenário Base" if base_margin else "Pendente",
                "tone": "approved" if base_margin else "insufficient",
                "sublabel": "Resultado líquido sobre receita líquida",
            },
            {
                "id": "ie_ivo_summary",
                "title": "IE / IVO (Resumo)",
                "value": f"IE: {ie_score}/100 | IVO: {ivo_score}/100",
                "badge": "Índices oficiais",
                "tone": "approved" if ivo_score >= 75 else "adjustments",
                "sublabel": "Evidência empírica e viabilidade de oferta",
            },
        ],
        "historical_trend": historical_series,
        "funnel_stages": funnel_stages,
        "ie_ivo_evolution": {
            "ie_score": ie_score,
            "ivo_score": ivo_score,
            "threshold": 75,
        },
        "dimension_indicators": dimension_indicators,
        "internal_benchmark": internal_benchmark,
        "analytical_highlights": highlights,
    }


def _build_fixed_competition_page(
    *,
    proposal: dict[str, Any],
    facts: DossierFacts,
    dossier: DossierOutput,
    ecosystem: dict[str, Any],
    pillar_rows: list[dict[str, Any]],
    claims_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    comp_bench = ecosystem.get("competitive_benchmark") if isinstance(ecosystem.get("competitive_benchmark"), dict) else {}
    rows = comp_bench.get("rows") if isinstance(comp_bench.get("rows"), list) else []
    monitored_total = int(comp_bench.get("monitored_total") or len(rows) or 0)
    offers_found = int(comp_bench.get("offers_found_count") or 0)
    whitespace_count = int(comp_bench.get("whitespace_count") or max(0, monitored_total - offers_found))

    pricing_audit = facts.analysis_audit.get("pricing") if isinstance(facts.analysis_audit, dict) else {}
    pricing_audit = pricing_audit if isinstance(pricing_audit, dict) else {}
    mean_price = pricing_audit.get("mean_total_brl")
    comparables = pricing_audit.get("comparables") if isinstance(pricing_audit.get("comparables"), list) else []
    prices_list = [
        float(c["total_brl"])
        for c in comparables
        if isinstance(c, dict) and isinstance(c.get("total_brl"), (int, float)) and float(c["total_brl"]) > 0
    ]
    for r in rows:
        if isinstance(r, dict) and isinstance(r.get("observed_price_brl"), (int, float)) and float(r["observed_price_brl"]) > 0:
            prices_list.append(float(r["observed_price_brl"]))

    if mean_price is None and prices_list:
        mean_price = sum(prices_list) / len(prices_list)
    min_price = min(prices_list) if prices_list else None
    max_price = max(prices_list) if prices_list else None

    if offers_found >= max(4, (monitored_total * 2) // 3) and monitored_total > 0:
        intensity_label = "Alta"
        intensity_tone = "risk"
    elif offers_found >= 2:
        intensity_label = "Média"
        intensity_tone = "adjustments"
    else:
        intensity_label = "Baixa / Moderada"
        intensity_tone = "approved"

    # 2x2 Positioning Map points (Price vs Workload/Depth)
    map_points: list[dict[str, Any]] = []
    max_p = max(prices_list) if prices_list else 20000.0
    min_p = min(prices_list) if len(prices_list) > 1 else 0.0
    span_p = max(1.0, max_p - min_p)

    for idx, r in enumerate(rows):
        if not isinstance(r, dict):
            continue
        has_offer = r.get("status") in {"direct_offer", "adjacent_offer"} or bool(r.get("has_direct_offer"))
        if not has_offer:
            continue
        p_val = r.get("observed_price_brl")
        x_pct = round(((float(p_val) - min_p) / span_p) * 70 + 15) if isinstance(p_val, (int, float)) and p_val > 0 else (25 + (idx * 17) % 55)
        y_pct = 72 if "Executiva" in str(r.get("category_label", "")) or "Acadêmica" in str(r.get("category_label", "")) else 48
        map_points.append(
            {
                "id": r.get("competitor_id") or f"comp-{idx}",
                "name": r.get("competitor_name") or "Concorrente",
                "x_pct": max(12, min(88, x_pct)),
                "y_pct": max(18, min(85, y_pct)),
                "price_label": r.get("price_display") or r.get("observed_price_display") or "—",
                "modality": r.get("modality") or "—",
            }
        )

    observed_signals: list[str] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        has_offer = r.get("status") in {"direct_offer", "adjacent_offer"} or bool(r.get("has_direct_offer"))
        if has_offer:
            price_lbl = r.get("price_display") or r.get("observed_price_display") or "—"
            observed_signals.append(
                f"{r.get('competitor_name')}: {r.get('observed_offer_title')} ({r.get('modality')}, {price_lbl})."
            )
    if not observed_signals:
        observed_signals.append("Nenhuma oferta direta qualificada foi observada nos concorrentes monitorados neste recorte.")

    ens_diff = _resolve_claim_items(list(dossier.highlights.pros), claims_by_id)
    actions_source = list(dossier.highlights.action_recommendations)
    actionable = [
        {
            "index": idx + 1,
            "area": act.area,
            "action": act.action,
            "priority": act.priority,
            "claim_ids": list(act.claim_ids),
        }
        for idx, act in enumerate(actions_source[:4])
    ]

    return {
        "monitored_total": monitored_total,
        "offers_found_count": offers_found,
        "whitespace_count": whitespace_count,
        "coverage_complete": bool(comp_bench.get("coverage_complete")),
        "kpis": [
            {
                "id": "mapped_competitors",
                "title": "Concorrentes Mapeados",
                "value": f"{offers_found} de {monitored_total}",
                "badge": f"{monitored_total} IES no catálogo fixo",
                "tone": "running",
                "sublabel": "Players com oferta identificada no recorte",
            },
            {
                "id": "competitive_intensity",
                "title": "Intensidade Competitiva",
                "value": intensity_label,
                "badge": f"{offers_found} ofertas ativas",
                "tone": intensity_tone,
                "sublabel": "Grau de disputa direta observada",
            },
            {
                "id": "price_band",
                "title": "Faixa Média de Preço",
                "value": _format_brl(mean_price) if isinstance(mean_price, (int, float)) else "Não observado",
                "badge": (
                    f"{_format_brl(min_price)} a {_format_brl(max_price)}"
                    if min_price is not None and max_price is not None
                    else "Sem faixa comparável"
                ),
                "tone": "adjustments" if mean_price else "insufficient",
                "sublabel": "Cursos comparáveis observados",
            },
            {
                "id": "positioning_gaps",
                "title": "Lacunas de Posicionamento",
                "value": f"{whitespace_count} players sem oferta",
                "badge": "Espaço competitivo",
                "tone": "approved" if whitespace_count > 0 else "adjustments",
                "sublabel": "Concorrentes monitorados sem oferta direta",
            },
        ],
        "competitor_rows": rows,
        "positioning_map": {
            "x_axis_label": "Preço Observado",
            "y_axis_label": "Profundidade / Escopo Executivo",
            "points": map_points,
            "opportunity_zone": {
                "label": "Espaço de oportunidade (ENS)",
                "description": f"Ticket proposto {_format_brl(proposal.get('ticket'))} · Carga {proposal.get('workload_hours') or '—'}h",
            },
        },
        "observed_signals": observed_signals[:5],
        "ens_differentiation": ens_diff[:4],
        "actionable_insights": actionable,
    }


def _build_sector_radar_page(
    *,
    facts: DossierFacts,
    dossier: DossierOutput,
    ecosystem: dict[str, Any],
    pillar_rows: list[dict[str, Any]],
    claims_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    radar_block = ecosystem.get("sector_radar") if isinstance(ecosystem.get("sector_radar"), dict) else {}
    signals = radar_block.get("signals") if isinstance(radar_block.get("signals"), list) else []
    monitored_total = int(
        radar_block.get("monitored_insurers_total") or radar_block.get("monitored_total") or 0
    )
    insurers_with_signals = int(
        radar_block.get("insurers_with_signals_count")
        or len({str(s.get("insurer_name") or s.get("actor_id")) for s in signals if isinstance(s, dict)})
    )

    pillar_by_key = {p["key"]: p["score"] for p in pillar_rows}
    attractiveness_score = round(

            pillar_by_key.get("search_and_media", 0) * 0.30
            + pillar_by_key.get("employability", 0) * 0.30
            + pillar_by_key.get("syllabus_fit", 0) * 0.20
            + pillar_by_key.get("internal_history", 0) * 0.20

    )

    search_score = pillar_by_key.get("search_and_media", 0)
    demand_trend_label = "Crescente" if search_score >= 70 else ("Estável" if search_score >= 50 else "Moderada")

    # Group signals by theme_detected
    theme_counts: dict[str, int] = {}
    for sig in signals:
        if not isinstance(sig, dict):
            continue
        theme = str(sig.get("theme_detected") or "Movimentação Setorial")
        theme_counts[theme] = theme_counts.get(theme, 0) + 1

    total_sigs = max(1, sum(theme_counts.values()))
    subthemes_distribution = [
        {
            "theme": theme,
            "count": count,
            "share_pct": round((count / total_sigs) * 100),
        }
        for theme, count in sorted(theme_counts.items(), key=lambda x: (-x[1], x[0]))
    ]

    radar_axes = [
        {"axis": "Demanda & Busca", "score": pillar_by_key.get("search_and_media", 0), "benchmark": 70},
        {"axis": "Empregabilidade", "score": pillar_by_key.get("employability", 0), "benchmark": 70},
        {"axis": "Espaço Competitivo", "score": pillar_by_key.get("paid_competition", 0), "benchmark": 65},
        {"axis": "Aderência Curricular", "score": pillar_by_key.get("syllabus_fit", 0), "benchmark": 75},
        {"axis": "Histórico ENS", "score": pillar_by_key.get("internal_history", 0), "benchmark": 75},
        {"axis": "Atratividade Preço", "score": pillar_by_key.get("pricing", 0), "benchmark": 65},
    ]

    strong_signals = [
        f"{s.get('insurer_name')}: {s.get('signal_title') or s.get('market_or_broker_pain')} ({s.get('theme_detected')})"
        for s in signals
        if isinstance(s, dict) and s.get("priority") == "primary"
    ][:4]
    if not strong_signals and signals:
        strong_signals = [
            f"{s.get('insurer_name')}: {s.get('signal_title') or s.get('market_or_broker_pain')}"
            for s in signals[:3]
            if isinstance(s, dict)
        ]

    weak_signals = list(facts.limitations[:3]) or list(facts.counterevidence[:3])
    executive_reading = _resolve_claim_items(list(dossier.executive_summary_claim_ids), claims_by_id)

    return {
        "attractiveness_score": attractiveness_score,
        "monitored_total": monitored_total,
        "insurers_with_signals_count": insurers_with_signals,
        "kpis": [
            {
                "id": "sector_attractiveness",
                "title": "Índice de Atratividade Setorial",
                "value": f"{attractiveness_score}/100",
                "badge": f"{insurers_with_signals}/{monitored_total} seguradoras com sinal" if monitored_total else "Score composto",
                "tone": "approved" if attractiveness_score >= 75 else "adjustments",
                "sublabel": "Demanda, empregabilidade e aderência",
            },
            {
                "id": "demand_trend",
                "title": "Tendência de Demanda",
                "value": demand_trend_label,
                "badge": f"Busca & Mídia {search_score}/100",
                "tone": "approved" if search_score >= 70 else "adjustments",
                "sublabel": "Comportamento de interesse externo",
            },
            {
                "id": "radar_coverage",
                "title": "Cobertura do Radar Setorial",
                "value": f"{insurers_with_signals} de {monitored_total}" if monitored_total else f"{len(signals)} sinais",
                "badge": "Seguradoras monitoradas",
                "tone": "running",
                "sublabel": "Atores do mercado segurador com evidência",
            },
            {
                "id": "employability_pressure",
                "title": "Relevância Profissional",
                "value": f"{pillar_by_key.get('employability', 0)}/100",
                "badge": "Mercado de trabalho",
                "tone": "approved" if pillar_by_key.get("employability", 0) >= 70 else "adjustments",
                "sublabel": "Sinais de vagas e competências demandadas",
            },
            {
                "id": "curriculum_fit",
                "title": "Potencial de Aplicação ENS",
                "value": "Alto" if pillar_by_key.get("syllabus_fit", 0) >= 75 else "Moderado",
                "badge": f"Ementa {pillar_by_key.get('syllabus_fit', 0)}/100",
                "tone": "approved" if pillar_by_key.get("syllabus_fit", 0) >= 75 else "adjustments",
                "sublabel": "Conexão dos sinais com o currículo",
            },
        ],
        "radar_axes": radar_axes,
        "subthemes_distribution": subthemes_distribution,
        "signals": signals,
        "strong_signals": strong_signals,
        "attention_signals": weak_signals,
        "executive_reading": executive_reading,
    }


def _build_economics_page(
    *,
    proposal: dict[str, Any],
    facts: DossierFacts,
    dossier: DossierOutput,
    economics: dict[str, Any],
    claims_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    econ_calculated = economics.get("status") == "calculated"
    scenarios = economics.get("scenarios") if isinstance(economics.get("scenarios"), list) else []
    base_scen = scenarios[1] if econ_calculated and len(scenarios) > 1 and isinstance(scenarios[1], dict) else (scenarios[0] if econ_calculated and scenarios and isinstance(scenarios[0], dict) else None)

    ticket_val = float(economics["ticket"]) if econ_calculated and economics.get("ticket") is not None else (float(proposal["ticket"]) if isinstance(proposal.get("ticket"), (int, float)) else None)
    fixed_costs_val = float(economics["fixed_costs"]) if econ_calculated and economics.get("fixed_costs") is not None else None
    var_cost_val = float(economics["variable_cost_per_student"]) if econ_calculated and economics.get("variable_cost_per_student") is not None else None
    be_students = economics.get("break_even_students") if econ_calculated else None

    if econ_calculated and base_scen:
        base_students = int(base_scen.get("students") or 0)
        net_rev = float(base_scen.get("net_revenue") or 0.0)
        total_costs = float(base_scen.get("total_costs") or 0.0)
        net_res = float(base_scen.get("net_result") or 0.0)
        gross_rev = round(ticket_val * base_students, 2) if ticket_val else net_rev
        deductions = max(0.0, round(gross_rev - net_rev, 2))
        fixed_c = fixed_costs_val or 0.0
        var_c = max(0.0, round(total_costs - fixed_c, 2))

        waterfall_steps = [
            {"label": "Receita Bruta", "value": gross_rev, "display": _format_brl(gross_rev), "kind": "total"},
            {"label": "Descontos / Impostos", "value": -deductions, "display": f"-{_format_brl(deductions)}" if deductions > 0 else "R$ 0", "kind": "negative"},
            {"label": "Custos Fixos (Turma)", "value": -fixed_c, "display": f"-{_format_brl(fixed_c)}", "kind": "negative"},
            {"label": "Custos Variáveis", "value": -var_c, "display": f"-{_format_brl(var_c)}" if var_c > 0 else "R$ 0", "kind": "negative"},
            {"label": "Resultado Líquido", "value": net_res, "display": _format_brl(net_res), "kind": "result"},
        ]

        # Deterministic Price/Discount x Volume sensitivity matrix
        sensitivity_rows: list[dict[str, Any]] = []
        vol_steps = [int(s.get("students") or 0) for s in scenarios[:3] if isinstance(s, dict)]
        for factor, label_suffix in ((0.90, "-10% desc."), (1.00, "Base"), (1.10, "+10% prêmio")):
            row_ticket = round((ticket_val or 0.0) * factor)
            cells: list[dict[str, str]] = []
            for st_count in vol_steps:
                sim_rev = row_ticket * st_count * (net_rev / gross_rev if gross_rev > 0 else 1.0)
                sim_cost = (fixed_c) + ((var_cost_val or 0.0) * st_count)
                sim_res = sim_rev - sim_cost
                sim_margin = round((sim_res / sim_rev) * 100) if sim_rev > 0 else 0
                cells.append(
                    {
                        "students": str(st_count),
                        "revenue_label": _format_brl(sim_rev),
                        "margin_label": f"{sim_margin}%",
                    }
                )
            sensitivity_rows.append(
                {
                    "ticket_label": f"{_format_brl(row_ticket)} ({label_suffix})",
                    "is_base": factor == 1.00,
                    "cells": cells,
                }
            )
    else:
        waterfall_steps = []
        sensitivity_rows = []

    assumptions_list: list[str] = []
    if ticket_val:
        assumptions_list.append(f"Ticket considerado: {_format_brl(ticket_val)}.")
    if fixed_costs_val is not None:
        assumptions_list.append(f"Custos fixos da turma: {_format_brl(fixed_costs_val)}.")
    if var_cost_val is not None:
        assumptions_list.append(f"Custo variável por aluno: {_format_brl(var_cost_val)}.")
    if not econ_calculated:
        assumptions_list.append(
            str(economics.get("message") or "Premissas completas de custo hora-aula, custos fixos e capacidade não foram informadas na proposta.")
        )

    risks_list = list(facts.limitations[:4])

    return {
        "status": "calculated" if econ_calculated else "assumptions_required",
        "message": str(economics.get("message") or ""),
        "kpis": [
            {
                "id": "expected_revenue",
                "title": "Receita Líquida (Cenário Base)",
                "value": _format_brl(float(base_scen["net_revenue"])) if econ_calculated and base_scen and base_scen.get("net_revenue") is not None else "Requer premissas",
                "badge": "Simulado em código" if econ_calculated else "Pendente",
                "tone": "approved" if econ_calculated else "insufficient",
                "sublabel": "Receita líquida estimada da turma base",
            },
            {
                "id": "ticket_avg",
                "title": "Ticket Total",
                "value": _format_brl(ticket_val) if ticket_val else "Não declarado",
                "badge": "Proposta ENS" if ticket_val else "Sem ticket",
                "tone": "running" if ticket_val else "insufficient",
                "sublabel": "Preço bruto por matrícula",
            },
            {
                "id": "net_margin",
                "title": "Margem Líquida (Base)",
                "value": str(base_scen.get("margin")) if econ_calculated and base_scen and base_scen.get("margin") else "Requer premissas",
                "badge": "Resultado / Receita" if econ_calculated else "Sem custos",
                "tone": "approved" if econ_calculated else "insufficient",
                "sublabel": "Margem operacional da turma simulada",
            },
            {
                "id": "break_even",
                "title": "Ponto de Equilíbrio",
                "value": f"{be_students} matrículas" if be_students is not None else "Requer premissas",
                "badge": f"Ocupação {economics.get('break_even_occupancy_rate', '—')}" if be_students is not None else "Custos não informados",
                "tone": "adjustments" if be_students is not None else "insufficient",
                "sublabel": "Volume mínimo para cobrir custos da turma",
            },
            {
                "id": "fixed_costs",
                "title": "Custos Fixos da Turma",
                "value": _format_brl(fixed_costs_val) if fixed_costs_val is not None else "Requer premissas",
                "badge": "Docência + operação" if fixed_costs_val is not None else "Pendente",
                "tone": "running" if fixed_costs_val is not None else "insufficient",
                "sublabel": "Hora-aula, coordenação e plataforma",
            },
            {
                "id": "net_result",
                "title": "Resultado Líquido (Base)",
                "value": _format_brl(float(base_scen["net_result"])) if econ_calculated and base_scen and base_scen.get("net_result") is not None else "Requer premissas",
                "badge": "Turma Base" if econ_calculated else "Premissa ausente",
                "tone": "approved" if econ_calculated else "insufficient",
                "sublabel": "Contribuição líquida após custos",
            },
        ],
        "waterfall_steps": waterfall_steps,
        "launch_scenarios": scenarios,
        "sensitivity_matrix": sensitivity_rows,
        "risks": risks_list,
        "assumptions": assumptions_list,
    }


def _build_swot_tows_page(
    *,
    facts: DossierFacts,
    dossier: DossierOutput,
    pillar_rows: list[dict[str, Any]],
    rec_meta: dict[str, str],
    claims_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    pros_claims = _resolve_claim_items(list(dossier.highlights.pros), claims_by_id)
    cons_claims = _resolve_claim_items(list(dossier.highlights.cons), claims_by_id)
    all_claims = _resolve_claim_items([c.claim_id for c in dossier.claims], claims_by_id)

    strengths: list[dict[str, Any]] = []
    for p in pillar_rows:
        if p["key"] in {"internal_history", "syllabus_fit"} and p["is_present"] and p["score"] >= 65:
            strengths.append(
                {
                    "text": f"{p['label']} com nota {p['score']}/100 ({p['status_label']}).",
                    "evidence_ids": ["scoring_result"],
                }
            )
    for c in pros_claims[:3]:
        strengths.append({"text": c["statement"], "evidence_ids": c["evidence_ids"]})

    weaknesses: list[dict[str, Any]] = []
    for lim in facts.limitations[:4]:
        weaknesses.append({"text": lim, "evidence_ids": ["scoring_result"]})

    opportunities: list[dict[str, Any]] = []
    for c in (pros_claims or all_claims)[:4]:
        opportunities.append({"text": c["statement"], "evidence_ids": c["evidence_ids"]})

    threats: list[dict[str, Any]] = []
    for c in cons_claims[:4]:
        threats.append({"text": c["statement"], "evidence_ids": c["evidence_ids"]})
    for ce in facts.counterevidence[:2]:
        threats.append({"text": ce, "evidence_ids": ["scoring_result"]})
    if not threats and facts.limitations:
        threats.append({"text": facts.limitations[0], "evidence_ids": ["scoring_result"]})

    # TOWS derived from action_recommendations & verified claims
    actions = list(dossier.highlights.action_recommendations)
    validations = list(dossier.highlights.validation_criteria)
    so_list = [a.action for a in actions if a.priority == "high"][:2] or [a.action for a in actions[:2]]
    st_list = [a.action for a in actions if a.area in {"commercial", "marketing"}][:2] or [a.action for a in actions[1:3]]
    wo_list = [v.criterion for v in validations[:2]] or [a.action for a in actions[:2]]
    wt_list = list(facts.limitations[:2]) or ["Garantir validação prévia das premissas operacionais antes da abertura de turma."]

    strategic_score = round(

            next((p["score"] for p in pillar_rows if p["key"] == "syllabus_fit"), 0) * 0.5
            + next((p["score"] for p in pillar_rows if p["key"] == "internal_history"), 0) * 0.5

    )

    priorities = [
        {
            "order": idx + 1,
            "title": act.action,
            "area": act.area,
            "priority_label": "Alta" if act.priority == "high" else ("Média" if act.priority == "medium" else "Baixa"),
            "priority_tone": "approved" if act.priority == "high" else "adjustments",
            "claim_ids": list(act.claim_ids),
        }
        for idx, act in enumerate(actions[:4])
    ]

    return {
        "kpis": [
            {
                "id": "strategic_criticality",
                "title": "Aderência Estratégica ENS",
                "value": f"{strategic_score}/100",
                "badge": "Histórico + Ementa",
                "tone": "approved" if strategic_score >= 75 else "adjustments",
                "sublabel": "Alinhamento institucional e curricular",
            },
            {
                "id": "positive_factors",
                "title": "Forças & Oportunidades (SO)",
                "value": f"{len(strengths) + len(opportunities)} fatores",
                "badge": "Alavancas",
                "tone": "approved",
                "sublabel": "Pontos fortes e oportunidades sustentadas",
            },
            {
                "id": "risk_factors",
                "title": "Fragilidades & Riscos (WT)",
                "value": f"{len(weaknesses) + len(threats)} alertas",
                "badge": "Mitigação",
                "tone": "adjustments" if (len(weaknesses) + len(threats)) <= 4 else "risk",
                "sublabel": "Limitações e ameaças mapeadas",
            },
            {
                "id": "strategic_positioning",
                "title": "Posicionamento Estratégico",
                "value": rec_meta["short_label"],
                "badge": rec_meta["label"],
                "tone": rec_meta["tone"],
                "sublabel": "Síntese de prontidão para lançamento",
            },
        ],
        "swot": {
            "strengths": strengths[:4],
            "weaknesses": weaknesses[:4],
            "opportunities": opportunities[:4],
            "threats": threats[:4],
        },
        "tows": {
            "so": so_list,
            "st": st_list,
            "wo": wo_list,
            "wt": wt_list,
        },
        "recommended_priorities": priorities,
        "executive_synthesis": dossier.executive_summary,
    }


def _build_viability_pillars_page(
    *,
    facts: DossierFacts,
    dossier: DossierOutput,
    economics: dict[str, Any],
    ecosystem: dict[str, Any],
    ivo_score: int,
    coverage_pct: int,
    confidence_pct: int,
    rec_meta: dict[str, str],
    pillar_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    comp_bench = ecosystem.get("competitive_benchmark") if isinstance(ecosystem.get("competitive_benchmark"), dict) else {}
    pricing_audit = facts.analysis_audit.get("pricing") if isinstance(facts.analysis_audit, dict) else {}
    pricing_audit = pricing_audit if isinstance(pricing_audit, dict) else {}
    internal_audit = facts.analysis_audit.get("internal_audit") if isinstance(facts.analysis_audit, dict) else {}
    internal_audit = internal_audit if isinstance(internal_audit, dict) else {}

    submetrics_by_key: dict[str, list[dict[str, str]]] = {
        "internal_history": [
            {"label": "Turmas comparáveis", "value": str(internal_audit.get("comparables_count") or 0)},
            {"label": "Média de alunos", "value": f"{round(float(internal_audit['mean_students']))}" if isinstance(internal_audit.get("mean_students"), (int, float)) else "—"},
            {"label": "Status na base", "value": "Aderente" if next((p["score"] for p in pillar_rows if p["key"] == "internal_history"), 0) >= 70 else "Parcial"},
        ],
        "paid_competition": [
            {"label": "IES monitoradas", "value": str(comp_bench.get("monitored_total") or 0)},
            {"label": "Ofertas diretas", "value": str(comp_bench.get("offers_found_count") or 0)},
            {"label": "Espaço livre", "value": f"{comp_bench.get('whitespace_count', 0)} IES"},
        ],
        "search_and_media": [
            {"label": "Evidências no pilar", "value": str(next((p["evidence_count"] for p in pillar_rows if p["key"] == "search_and_media"), 0))},
            {"label": "Sinal de interesse", "value": "Crescente" if next((p["score"] for p in pillar_rows if p["key"] == "search_and_media"), 0) >= 70 else "Moderado"},
            {"label": "Cobertura de busca", "value": "Ativa" if next((p["is_present"] for p in pillar_rows if p["key"] == "search_and_media"), False) else "Ausente"},
        ],
        "employability": [
            {"label": "Evidências de vagas", "value": str(next((p["evidence_count"] for p in pillar_rows if p["key"] == "employability"), 0))},
            {"label": "Demanda profissional", "value": "Alta" if next((p["score"] for p in pillar_rows if p["key"] == "employability"), 0) >= 75 else "Moderada"},
            {"label": "Sinais setoriais", "value": str(len((ecosystem.get("sector_radar") or {}).get("signals") or []))},
        ],
        "syllabus_fit": [
            {"label": "Alinhamento ao portfólio", "value": "Alto" if next((p["score"] for p in pillar_rows if p["key"] == "syllabus_fit"), 0) >= 75 else "Adequado"},
            {"label": "Ações curriculares", "value": str(len(dossier.highlights.action_recommendations))},
            {"label": "Público-alvo", "value": (facts.target_audience or "Definido")[:18]},
        ],
        "pricing": [
            {"label": "Preços comparáveis", "value": str(pricing_audit.get("comparables_count") or 0)},
            {"label": "Média de mercado", "value": _format_brl(pricing_audit.get("mean_total_brl")) if isinstance(pricing_audit.get("mean_total_brl"), (int, float)) else "—"},
            {"label": "Modelagem de turma", "value": "Calculada" if economics.get("status") == "calculated" else "Requer custos"},
        ],
    }

    pillar_cards: list[dict[str, Any]] = []
    justifications: list[dict[str, str]] = []
    for row in pillar_rows:
        card = {
            **row,
            "submetrics": submetrics_by_key.get(row["key"], []),
        }
        pillar_cards.append(card)
        justifications.append(
            {
                "label": row["label"],
                "text": (
                    f"Nota {row['score']}/100 (peso {row['weight_pct']}% → contribuição de {row['contribution_pts']} pts no IVO). "
                    f"Classificação: {row['status_label']}."
                ),
            }
        )

    return {
        "ivo_score": ivo_score,
        "coverage_pct": coverage_pct,
        "confidence_pct": confidence_pct,
        "pillar_cards": pillar_cards,
        "weight_score_matrix": pillar_rows,
        "pillar_justifications": justifications,
        "synthesis_text": dossier.executive_summary,
        "recommendation_code": facts.recommendation,
        "recommendation_label": rec_meta["label"],
        "recommendation_short": rec_meta["short_label"],
        "recommendation_tone": rec_meta["tone"],
    }


def _build_revisions_page(
    *,
    facts: DossierFacts,
    dossier: DossierOutput,
    rec_meta: dict[str, str],
    claims_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    default_areas = [
        {
            "area": "marketing",
            "label": "Marketing",
            "icon": "megaphone",
            "status": "PENDING",
            "status_label": "Pendente",
            "tone": "insufficient",
            "reviewer_name": "Aguardando revisão",
            "updated_at_label": "Disponível para parecer",
            "comment": "",
        },
        {
            "area": "produto",
            "label": "Produto",
            "icon": "box",
            "status": "PENDING",
            "status_label": "Pendente",
            "tone": "insufficient",
            "reviewer_name": "Aguardando revisão",
            "updated_at_label": "Disponível para parecer",
            "comment": "",
        },
        {
            "area": "comercial",
            "label": "Comercial",
            "icon": "briefcase",
            "status": "PENDING",
            "status_label": "Pendente",
            "tone": "insufficient",
            "reviewer_name": "Aguardando revisão",
            "updated_at_label": "Disponível para parecer",
            "comment": "",
        },
        {
            "area": "financeiro",
            "label": "Financeiro",
            "icon": "dollar-sign",
            "status": "PENDING",
            "status_label": "Pendente",
            "tone": "insufficient",
            "reviewer_name": "Aguardando revisão",
            "updated_at_label": "Disponível para parecer",
            "comment": "",
        },
    ]

    pendencies = [
        {
            "criterion": v.criterion,
            "target": v.target,
            "status": v.status,
            "claim_ids": list(v.claim_ids),
        }
        for v in dossier.highlights.validation_criteria
    ]
    if not pendencies and facts.limitations:
        pendencies = [
            {
                "criterion": lim,
                "target": "Governança & Premissas",
                "status": "pending",
                "claim_ids": [],
            }
            for lim in facts.limitations[:3]
        ]

    next_steps = [
        {
            "order": idx + 1,
            "action": act.action,
            "area": act.area,
            "priority": act.priority,
        }
        for idx, act in enumerate(dossier.highlights.action_recommendations[:4])
    ]

    tfr = dossier.three_fold_review
    audit_changes = [
        {
            "index": 1,
            "description": "Publicação inicial do Dossiê Executivo de Viabilidade no template CMS (9 subpáginas)",
            "area": "IA & Verificador",
            "owner": "Motor Prometeus",
            "impact": "Alto",
        },
        {
            "index": 2,
            "description": f"Auditoria de integridade de dados e cobertura ({round(facts.coverage_score * 100)}% cobertura · {round(facts.confidence_score * 100)}% confiança)",
            "area": "Fontes & Evidências",
            "owner": "DossierVerifier",
            "impact": "Médio",
        },
        {
            "index": 3,
            "description": (
                tfr.summary
                if tfr and tfr.summary
                else f"Validação numérica e de afirmações ({len(dossier.claims)} afirmações verificadas)"
            ),
            "area": "Governança",
            "owner": "Revisão Tripla",
            "impact": "Alto",
        },
    ]

    return {
        "area_reviews": default_areas,
        "overall_progress": {
            "approved_count": 0,
            "total_areas": 4,
            "percent": 0,
            "status_label": "Aguardando aprovação das áreas",
            "tone": "adjustments",
        },
        "version_history": [
            {
                "version": "v1.0",
                "is_current": True,
                "badge_label": "Base publicada",
                "tone": "approved",
                "timestamp_label": "Publicação automática verificada",
                "description": "Primeira versão do dossiê consolidada e auditada pelo verificador determinístico.",
            }
        ],
        "comments_feed": [],
        "changes_summary": audit_changes,
        "pendencies": pendencies,
        "approval_recommendation": {
            "decision_label": rec_meta["approval_label"],
            "tone": rec_meta["tone"],
            "note": rec_meta["approval_note"],
        },
        "next_steps": next_steps,
    }


def _build_sources_evidences_page(
    *,
    facts: DossierFacts,
    dossier: DossierOutput,
    ecosystem: dict[str, Any],
    coverage_pct: int,
    confidence_pct: int,
    ie_score: int,
    pillar_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    # Group fact items by source_type
    by_type: dict[str, list[Any]] = {}
    for item in facts.items:
        by_type.setdefault(str(item.source_type), []).append(item)

    comp_bench = ecosystem.get("competitive_benchmark") if isinstance(ecosystem.get("competitive_benchmark"), dict) else {}
    radar_block = ecosystem.get("sector_radar") if isinstance(ecosystem.get("sector_radar"), dict) else {}
    internal_audit = facts.analysis_audit.get("internal_audit") if isinstance(facts.analysis_audit, dict) else {}
    internal_audit = internal_audit if isinstance(internal_audit, dict) else {}

    source_catalog = [
        {
            "source_name": "Google Trends & Volume de Busca",
            "source_type": "Tendência & Demanda",
            "status_label": "Coletado" if by_type.get("SEARCH_VOLUME") or by_type.get("TREND") else "Parcial",
            "status_tone": "approved" if by_type.get("SEARCH_VOLUME") or by_type.get("TREND") else "adjustments",
            "records_count": len(by_type.get("SEARCH_VOLUME", [])) + len(by_type.get("TREND", [])),
            "observation": "Séries e indicadores de interesse de busca para os termos-chave do curso.",
        },
        {
            "source_name": "Sites de Concorrentes (Catálogo Fixo ENS)",
            "source_type": "Concorrência Educacional",
            "status_label": "Coletado" if comp_bench.get("offers_found_count") or by_type.get("OFFER") else "Monitorado",
            "status_tone": "approved" if comp_bench.get("offers_found_count") or by_type.get("OFFER") else "running",
            "records_count": len(by_type.get("OFFER", [])) + len(by_type.get("PAID_COMPETITION", [])),
            "observation": f"Monitoramento de {comp_bench.get('monitored_total', 10)} IES concorrentes configuradas.",
        },
        {
            "source_name": "LinkedIn Jobs & Mercado de Trabalho",
            "source_type": "Vagas / Empregabilidade",
            "status_label": "Coletado" if by_type.get("JOB_MARKET") else "Parcial",
            "status_tone": "approved" if by_type.get("JOB_MARKET") else "adjustments",
            "records_count": len(by_type.get("JOB_MARKET", [])),
            "observation": "Levantamento de vagas abertas, salários e competências requisitadas.",
        },
        {
            "source_name": "Radar Setorial (Seguradoras)",
            "source_type": "Pulso do Setor Segurador",
            "status_label": "Coletado" if radar_block.get("signals") else "Monitorado",
            "status_tone": "approved" if radar_block.get("signals") else "running",
            "records_count": len(radar_block.get("signals") or []),
            "observation": f"Sinais institucionais e redes sociais de {radar_block.get('monitored_total', 10)} seguradoras.",
        },
        {
            "source_name": "Redes Sociais & Mídia (Instagram / YouTube / Ads)",
            "source_type": "Mídia Social & Publicidade",
            "status_label": "Coletado" if by_type.get("SOCIAL_MEDIA") or by_type.get("VIDEO_CONTENT") else "Parcial",
            "status_tone": "approved" if by_type.get("SOCIAL_MEDIA") or by_type.get("VIDEO_CONTENT") else "adjustments",
            "records_count": len(by_type.get("SOCIAL_MEDIA", [])) + len(by_type.get("VIDEO_CONTENT", [])),
            "observation": "Publicações, engajamento temático e anúncios patrocinados.",
        },
        {
            "source_name": "Catálogo Histórico ENS",
            "source_type": "Base Institucional",
            "status_label": "Coletado" if internal_audit.get("comparables_count") else "Consultado",
            "status_tone": "approved" if internal_audit.get("comparables_count") else "running",
            "records_count": int(internal_audit.get("comparables_count") or 0),
            "observation": "Histórico de turmas, alunos matriculados e retenção da ENS.",
        },
    ]

    coverage_bars = [
        {
            "label": "Demanda & Interesse (Buscas e Mídia)",
            "pct": next((p["score"] for p in pillar_rows if p["key"] == "search_and_media"), 0),
        },
        {
            "label": "Concorrência & Oferta Educacional",
            "pct": next((p["score"] for p in pillar_rows if p["key"] == "paid_competition"), 0),
        },
        {
            "label": "Empregabilidade & Mercado",
            "pct": next((p["score"] for p in pillar_rows if p["key"] == "employability"), 0),
        },
        {
            "label": "Histórico ENS & Aderência Curricular",
            "pct": round(
                (
                    next((p["score"] for p in pillar_rows if p["key"] == "internal_history"), 0)
                    + next((p["score"] for p in pillar_rows if p["key"] == "syllabus_fit"), 0)
                )
                / 2.0
            ),
        },
    ]

    evidence_categories = [
        {
            "id": "search_trends",
            "title": "Tendências de Busca & Mídia",
            "description": "Sinais de procura orgânica, interesse temático e conteúdo digital.",
            "evidence_ids": [i.evidence_id for i in facts.items if i.source_type in {"SEARCH_VOLUME", "TREND", "VIDEO_CONTENT"}][:8],
        },
        {
            "id": "competition_signals",
            "title": "Sinais da Concorrência",
            "description": "Ofertas identificadas, posicionamento de preço e formatos das IES.",
            "evidence_ids": [i.evidence_id for i in facts.items if i.source_type in {"OFFER", "PAID_COMPETITION"}][:8],
        },
        {
            "id": "historical_fit",
            "title": "Aderência Histórica & Ementa",
            "description": "Desempenho das edições comparáveis da ENS e aderência curricular.",
            "evidence_ids": ["scoring_result", *[i.evidence_id for i in facts.items if i.source_type in {"INSTITUTIONAL", "ACADEMIC"}][:6]],
        },
        {
            "id": "professional_demand",
            "title": "Demanda Profissional & Radar",
            "description": "Vagas abertas no mercado e sinais das seguradoras monitoradas.",
            "evidence_ids": [i.evidence_id for i in facts.items if i.source_type in {"JOB_MARKET", "SOCIAL_MEDIA"}][:8],
        },
    ]

    method_steps = [
        {
            "step": 1,
            "title": "Coleta",
            "description": "Levantamento automatizado em fontes primárias, concorrentes fixos e radar setorial.",
        },
        {
            "step": 2,
            "title": "Preparação",
            "description": "Preservação bruta, normalização e reconciliação auditável de leitura integral.",
        },
        {
            "step": 3,
            "title": "Classificação",
            "description": "Separação estrita entre concorrência educacional direta e contexto setorial.",
        },
        {
            "step": 4,
            "title": "Score",
            "description": "Ponderação determinística nos 6 pilares do modelo portfolio-v2 (IVO e IE).",
        },
        {
            "step": 5,
            "title": "Decisão",
            "description": "Síntese executiva verificada pelo DossierVerifier e publicada no CMS.",
        },
    ]

    return {
        "collected_sources": source_catalog,
        "coverage_pct": coverage_pct,
        "confidence_pct": confidence_pct,
        "ie_score": ie_score,
        "coverage_bars": coverage_bars,
        "evidence_categories": evidence_categories,
        "method_steps": method_steps,
    }
