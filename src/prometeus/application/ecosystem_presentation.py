"""Construção determinística dos blocos visuais de Benchmark Competitivo e Radar Setorial para o Dossiê."""

from __future__ import annotations

import re
from typing import Any

from prometeus.application.research_scope import (
    match_configured_competitor,
    match_sector_radar_actor,
)
from prometeus.application.sector_radar import _channel_and_scope, _detect_theme
from prometeus.domain.dossiers import DossierFactItem, DossierFacts

CATEGORY_LABELS: dict[str, str] = {
    "direct_specialist": "Especialista em Seguros",
    "executive_business": "Escola Executiva",
    "technical_academic": "Acadêmica Técnica",
    "scale_ead": "EAD de Escala",
    "legal_niche": "Nicho Jurídico",
    "tech_edtech": "Tech & EdTech",
}


def _extract_modality(text: str) -> str:
    lower = text.lower()
    if "ead live" in lower or "ao vivo" in lower or "síncron" in lower or "sincron" in lower:
        return "EAD Live"
    if "presencial" in lower and ("híbrid" in lower or "hibrid" in lower):
        return "Híbrido"
    if "presencial" in lower:
        return "Presencial"
    if "assíncron" in lower or "assincron" in lower or "ead" in lower or "online" in lower:
        return "Online / EAD"
    return "—"


def _observed_price_display(
    item: DossierFactItem,
    comparable_prices: dict[str, float],
) -> tuple[float | None, str]:
    metrics = item.key_metrics
    for key in ("price_brl", "total_price_brl", "total_price", "priceBrl", "tuition_brl"):
        val = metrics.get(key)
        if isinstance(val, (int, float)) and not isinstance(val, bool) and val > 0:
            formatted = f"R$ {float(val):,.0f}".replace(",", ".")
            return float(val), formatted
    comp_val = comparable_prices.get(item.evidence_id)
    if comp_val is not None and comp_val > 0:
        formatted = f"R$ {float(comp_val):,.0f}".replace(",", ".")
        return float(comp_val), formatted
    return None, "—"


def _differentiation_note(category: str, has_offer: bool) -> str:
    if not has_offer:
        return "Janela de pioneirismo (whitespace acadêmico) para posicionamento vertical da ENS."
    mapping = {
        "direct_specialist": "ENS agrega chancela de escola de negócios, profundidade executiva e networking corporativo.",
        "executive_business": "ENS diferencia-se pela especialização vertical em seguros, regulação SUSEP e casos de sinistros/subscrição.",
        "technical_academic": "ENS equilibra rigor técnico-atuarial com aplicação gerencial imediata no mercado segurador.",
        "scale_ead": "ENS posiciona-se em faixa executiva premium com corpo docente atuante no setor e curadoria técnica.",
        "legal_niche": "ENS conecta o marco jurídico-regulatório à operação técnica, subscrição e gestão de produtos securitários.",
        "tech_edtech": "ENS traduz tecnologia e IA para a realidade regulada de subscrição, corretagem e sinistros.",
    }
    return mapping.get(
        category,
        "ENS combina autoridade institucional no setor de seguros com aplicabilidade prática.",
    )


def _curriculum_connection_for_theme(theme: str) -> str:
    lower = theme.lower()
    if "ia" in lower or "automacao" in lower or "subscricao" in lower:
        return "Sustenta módulos de subscrição assistida, automação e análise preditiva de riscos."
    if "sinistro" in lower or "operac" in lower:
        return "Sustenta oficinas práticas de regulação digital de sinistros e mitigação de fraudes."
    if "corretor" in lower or "distribuicao" in lower:
        return "Endereça dores comerciais e consultivas reais da rede de corretores parceiros."
    if "saude" in lower or "vida" in lower or "previdencia" in lower:
        return "Alinha estudos de caso às linhas de pessoas, benefícios e equilíbrio técnico."
    return "Conecta a ementa às demandas estratégicas atuais das seguradoras empregadoras."


def build_ecosystem_presentation_blocks(
    proposal: dict[str, Any],
    facts: DossierFacts,
    proposed_workload_hours: int,
) -> dict[str, Any]:
    """Gera `competitive_benchmark` e `sector_radar` com rastreabilidade estrita a `evidence_ids`."""
    institution_ctx = (
        dict(proposal.get("_institution_context"))
        if isinstance(proposal.get("_institution_context"), dict)
        else {}
    )
    competitors = [
        c for c in institution_ctx.get("competitors", []) if isinstance(c, dict) and c.get("id")
    ]
    radar_actors = [
        s for s in institution_ctx.get("sector_radar", []) if isinstance(s, dict) and s.get("id")
    ]

    result: dict[str, Any] = {}

    # 1. Matriz de Concorrência Educacional Fixa
    if competitors:
        plan_calls = (
            facts.research_plan.get("tool_calls", [])
            if isinstance(facts.research_plan, dict)
            else []
        )
        queried_text = " ".join(
            str(call.get("query") or "").lower()
            for call in plan_calls
            if isinstance(call, dict)
        )
        has_any_plan_calls = bool(plan_calls)

        comparable_prices: dict[str, float] = {}
        pricing_audit = facts.analysis_audit.get("pricing")
        if isinstance(pricing_audit, dict):
            raw_comparables = pricing_audit.get("comparables")
            if isinstance(raw_comparables, list):
                for entry in raw_comparables:
                    if not isinstance(entry, dict):
                        continue
                    total_brl = entry.get("total_brl")
                    eids = entry.get("evidence_ids")
                    if (
                        isinstance(total_brl, (int, float))
                        and not isinstance(total_brl, bool)
                        and total_brl > 0
                        and isinstance(eids, list)
                    ):
                        for eid in eids:
                            if eid:
                                comparable_prices[str(eid)] = float(total_brl)

        by_comp: dict[str, list[DossierFactItem]] = {str(c["id"]): [] for c in competitors}
        for item in facts.items:
            if item.source_type not in {"OFFER", "PAID_COMPETITION"}:
                continue
            if item.key_metrics.get("evidence_role") == "context_only":
                continue
            if item.key_metrics.get("actor_role") == "sector_radar":
                continue
            matched_id = str(item.key_metrics.get("matched_actor_id") or "")
            if not matched_id or matched_id not in by_comp:
                matched_comp = match_configured_competitor(
                    item.key_metrics, item.source_url or "", institution_ctx
                )
                matched_id = str(matched_comp.get("id") or "") if matched_comp else ""
            if matched_id in by_comp:
                by_comp[matched_id].append(item)

        rows: list[dict[str, Any]] = []
        offers_found = 0
        for comp in competitors:
            comp_id = str(comp["id"])
            comp_name = str(comp.get("name") or comp_id)
            category = str(comp.get("category") or "executive_business")
            cat_label = CATEGORY_LABELS.get(category, "Instituição de Ensino")
            matched_items = by_comp.get(comp_id, [])

            if matched_items:
                offers_found += 1
                best = sorted(
                    matched_items,
                    key=lambda it: (
                        1 if _observed_price_display(it, comparable_prices)[0] is not None else 0
                    ),
                    reverse=True,
                )[0]
                _, price_display = _observed_price_display(best, comparable_prices)
                raw_hours = best.key_metrics.get("workload_hours")
                obs_hours = (
                    int(raw_hours)
                    if isinstance(raw_hours, (int, float))
                    and not isinstance(raw_hours, bool)
                    and raw_hours > 0
                    else None
                )
                hours_display = f"{obs_hours}h" if obs_hours is not None else "—"
                is_adjacent = category in {"direct_specialist", "tech_edtech"} or (
                    obs_hours is not None and obs_hours < 120 and proposed_workload_hours >= 180
                )
                status = "adjacent_offer" if is_adjacent else "direct_offer"
                modality = _extract_modality(f"{best.title} {best.summary}")
                rows.append(
                    {
                        "competitor_id": comp_id,
                        "name": comp_name,
                        "category_label": cat_label,
                        "status": status,
                        "observed_offer_title": best.title,
                        "modality": modality,
                        "workload_hours": hours_display,
                        "price_display": price_display,
                        "ens_differentiation": _differentiation_note(category, has_offer=True),
                        "evidence_ids": list(dict.fromkeys(it.evidence_id for it in matched_items)),
                    }
                )
            else:
                domains = [str(d).lower() for d in comp.get("domains", []) if d]
                was_queried = (not has_any_plan_calls) or any(
                    f"site:{d}" in queried_text or d in queried_text for d in domains
                )
                status = "no_offer_observed" if was_queried else "not_queried"
                title_msg = (
                    "Nenhuma oferta específica observada no tema"
                    if was_queried
                    else "Domínio fora do lote consultado nesta rodada"
                )
                rows.append(
                    {
                        "competitor_id": comp_id,
                        "name": comp_name,
                        "category_label": cat_label,
                        "status": status,
                        "observed_offer_title": title_msg,
                        "modality": "—",
                        "workload_hours": "—",
                        "price_display": "—",
                        "ens_differentiation": _differentiation_note(category, has_offer=False),
                        "evidence_ids": [],
                    }
                )

        whitespace_count = sum(1 for r in rows if r["status"] == "no_offer_observed")
        result["competitive_benchmark"] = {
            "monitored_total": len(competitors),
            "offers_found_count": offers_found,
            "whitespace_summary": (
                f"{offers_found} de {len(competitors)} instituições concorrentes monitoradas apresentaram "
                f"oferta correlata observada; {whitespace_count} consultadas não exibiram curso específico no recorte."
            ),
            "rows": rows,
        }

    # 2. Pulso do Radar Setorial Permanente (Seguradoras / Ecossistema Empregador)
    baseline = (
        facts.analysis_audit.get("sector_radar_baseline")
        if isinstance(facts.analysis_audit.get("sector_radar_baseline"), dict)
        else None
    )
    if radar_actors or (baseline and baseline.get("signals")):
        actor_by_id = {str(a["id"]): a for a in radar_actors}
        signals_out: list[dict[str, Any]] = []
        seen_actor_urls: set[tuple[str, str]] = set()

        for item in facts.items:
            matched_actor: dict[str, Any] | None = None
            if item.key_metrics.get("actor_role") == "sector_radar":
                aid = str(item.key_metrics.get("matched_actor_id") or "")
                matched_actor = actor_by_id.get(aid) or {
                    "id": aid or "sector-actor",
                    "name": str(item.key_metrics.get("matched_actor_name") or item.title),
                    "priority": "secondary",
                    "monitoring_focus": [],
                    "social": {"linkedin_scope": item.key_metrics.get("linkedin_scope", "national")},
                }
            elif radar_actors:
                matched_actor = match_sector_radar_actor(
                    item.key_metrics, item.source_url or "", institution_ctx
                )

            if matched_actor is None:
                continue

            actor_id = str(matched_actor.get("id") or "sector-actor")
            url = str(item.source_url or "")
            key = (actor_id, url.lower().rstrip("/"))
            if key in seen_actor_urls:
                continue
            seen_actor_urls.add(key)

            channel_label, scope_badge = _channel_and_scope(url, matched_actor)
            if (
                str(item.key_metrics.get("linkedin_scope") or "") == "global"
                and ("linkedin" in url.lower() or "linkedin" in item.title.lower())
            ):
                channel_label = "LinkedIn"
                scope_badge = "Global (contextual)"

            clean_summary = re.sub(
                r"^Evidência de mercado tipo [A-Z_]+:\s*", "", item.summary
            ).replace(
                "Contexto do setor; não é oferta concorrente nem comprovação de demanda pela formação.",
                "",
            )
            clean_summary = re.sub(r"\s+—\s+—\s+", " — ", clean_summary).strip(" —")
            pain_excerpt = (clean_summary or item.title)[:260]
            theme = _detect_theme(
                f"{item.title} {pain_excerpt}",
                list(matched_actor.get("monitoring_focus") or []),
            )
            signals_out.append(
                {
                    "actor_id": actor_id,
                    "insurer_name": str(matched_actor.get("name") or actor_id),
                    "priority": str(matched_actor.get("priority") or "secondary"),
                    "channel_label": channel_label,
                    "scope_badge": scope_badge,
                    "theme_detected": theme,
                    "market_or_broker_pain": pain_excerpt,
                    "curriculum_link": _curriculum_connection_for_theme(theme),
                    "source_url": url,
                    "evidence_ids": [item.evidence_id],
                }
            )

        if baseline and isinstance(baseline.get("signals"), list):
            for bsig in baseline["signals"]:
                if not isinstance(bsig, dict):
                    continue
                actor_id = str(bsig.get("actor_id") or "")
                url = str(bsig.get("source_url") or "")
                key = (actor_id, url.lower().rstrip("/"))
                if key in seen_actor_urls:
                    continue
                seen_actor_urls.add(key)
                theme = str(bsig.get("theme_detected") or "Movimentação Setorial")
                signals_out.append(
                    {
                        "actor_id": actor_id,
                        "insurer_name": str(bsig.get("insurer_name") or actor_id),
                        "priority": str(bsig.get("priority") or "secondary"),
                        "channel_label": str(bsig.get("channel_label") or "Web Institucional"),
                        "scope_badge": str(bsig.get("scope_badge") or "Brasil"),
                        "theme_detected": theme,
                        "market_or_broker_pain": str(bsig.get("market_or_broker_pain") or "")[:260],
                        "curriculum_link": _curriculum_connection_for_theme(theme),
                        "source_url": url,
                        "evidence_ids": [],
                    }
                )

        signals_out.sort(key=lambda s: (0 if s["priority"] == "primary" else 1, s["insurer_name"]))
        covered_names = list(dict.fromkeys(s["insurer_name"] for s in signals_out))
        monitored_total = len(radar_actors) or int(
            baseline.get("monitored_actors_count", 0) if baseline else 0
        )
        pulse = (
            f"{len(signals_out)} sinal(is) contextual(is) capturado(s) em {len(covered_names)} de {monitored_total} "
            "seguradoras monitoradas (mercado empregador e dores de corretores — nunca contabilizadas como concorrentes de curso)."
            if signals_out
            else f"Monitoramento configurado para {monitored_total} seguradoras de referência; nenhum sinal específico adicional observado nesta rodada."
        )
        result["sector_radar"] = {
            "monitored_insurers_total": monitored_total,
            "baseline_collected_at": baseline.get("collected_at") if baseline else None,
            "signals_count": len(signals_out),
            "executive_pulse": pulse,
            "signals": signals_out[:12],
        }

    return result
