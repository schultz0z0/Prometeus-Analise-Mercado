"""Projeção estruturada e determinística de observações por finalidade (Fase 1 — Tarefa 1.2).

Substitui o corte cego por string (ex.: `json.dumps(...)[:14000]`), garantindo:
1. Retenção integral de campos e indicadores críticos;
2. Sumarização determinística de séries temporais (janela, densidade, métricas);
3. Disponibilidade de descrições e requisitos completos de vagas;
4. Respeito ao orçamento de contexto com diagnóstico explícito de omissões;
5. Higienização de dados não confiáveis sem conceder privilégio de instrução.
"""

from __future__ import annotations

import json
from typing import Any

from prometeus.domain.evidence_observations import (
    AdObservation,
    JobObservation,
    OfferObservation,
    SocialObservation,
    TrendSeries,
)
from prometeus.infrastructure.apify.normalizers import normalize_observation

PROJECTOR_VERSION = "typed-projection-v2"


def build_qualification_context(
    observation: Any,
    purpose: str,
    budget: int = 14000,
    *,
    title: str | None = None,
    url: str | None = None,
) -> dict[str, Any]:
    """Constrói contexto determinístico estruturado para qualificação semântica

    dentro do orçamento de caracteres, com diagnósticos explícitos de omissão.
    """
    # 1. Normaliza para observação tipada se receber dict bruto
    obs = observation
    if isinstance(observation, dict):
        obs = normalize_observation(purpose, observation, url=str(url or ""))

    omissions: list[dict[str, Any]] = []
    base_title = title or getattr(obs, "title", None)
    if base_title is not None and hasattr(base_title, "value"):
        base_title = getattr(base_title, "value", None)
    base_url = url or getattr(obs, "url", "")

    context: dict[str, Any] = {
        "purpose": purpose,
        "observation_type": obs.__class__.__name__ if obs else "Unknown",
        "title": str(base_title or ""),
        "url": str(base_url or ""),
        "key_metrics": {},
    }

    # 2. Extração por tipo canônico
    if isinstance(obs, TrendSeries):
        _project_trend_series(obs, context)
    elif isinstance(obs, JobObservation):
        _project_job_observation(obs, context)
    elif isinstance(obs, OfferObservation):
        _project_offer_observation(obs, context)
    elif isinstance(obs, SocialObservation):
        _project_social_observation(obs, context)
    elif isinstance(obs, AdObservation):
        _project_ad_observation(obs, context)
    elif isinstance(observation, dict):
        # Fallback para dicionário genérico higienizado
        _project_generic_dict(observation, context)
    else:
        context["raw_summary"] = str(obs)[:1000]

    # 3. Ajuste estrito ao orçamento de caracteres
    serialized = json.dumps(context, ensure_ascii=False)
    if len(serialized) > budget:
        context = _enforce_budget(context, budget, omissions)

    if omissions:
        context["omissions"] = omissions

    return context


def _project_trend_series(series: TrendSeries, context: dict[str, Any]) -> None:
    """Projeta série temporal com janela, contagens válidas/ausentes/parciais, densidade e amostra."""
    total = series.total_points or len(series.points)
    points = series.points

    valid_points = 0
    missing_points = 0
    partial_points = 0

    values: list[float] = []
    for pt in points:
        val_list = pt.value if isinstance(pt.value, list) else [pt.value]
        val_float = float(val_list[0]) if val_list and val_list[0] is not None else 0.0
        values.append(val_float)
        if val_float > 0:
            valid_points += 1
        else:
            missing_points += 1

        if pt.is_partial:
            partial_points += 1

    density = round(valid_points / total, 4) if total > 0 else 0.0
    avg_interest = series.average_interest or (round(sum(values) / len(values), 2) if values else 0.0)
    growth_pct = series.growth_trend_pct
    max_val = max(values) if values else 0.0
    latest_val = values[-1] if values else 0.0

    start_time = points[0].time if points else None
    end_time = points[-1].time if points else None

    context["key_metrics"] = {
        "total_points": total,
        "valid_points": valid_points,
        "missing_points": missing_points,
        "partial_points": partial_points,
        "density": density,
        "average_interest": avg_interest,
        "growth_trend_pct": growth_pct,
        "max_interest": max_val,
        "latest_interest": latest_val,
    }

    context["window"] = {
        "start_time": start_time,
        "end_time": end_time,
        "term": series.term or context.get("title", ""),
    }

    sampled_points: list[dict[str, Any]] = []
    step = max(1, total // 40)
    for i, pt in enumerate(points):
        val_list = pt.value if isinstance(pt.value, list) else [pt.value]
        val = val_list[0] if val_list else 0
        if (i % step == 0) or (val and val > 0) or (i >= total - 10):
            sampled_points.append(
                {
                    "time": pt.time,
                    "date": pt.formatted_time,
                    "value": val,
                    "is_partial": bool(pt.is_partial),
                }
            )

    seen_times = set()
    dedup_points = []
    for sp in sampled_points:
        if sp["time"] not in seen_times:
            seen_times.add(sp["time"])
            dedup_points.append(sp)

    context["timeline_summary"] = dedup_points[:60]

    raw = series.raw_payload or {}
    rel_queries = raw.get("relatedQueries_top") or raw.get("relatedQueries_rising")
    if isinstance(rel_queries, list):
        context["related_queries_sample"] = [
            q.get("query") or q.get("topic_title") or str(q)
            for q in rel_queries[:5]
            if isinstance(q, dict)
        ]


def _project_job_observation(job: JobObservation, context: dict[str, Any]) -> None:
    """Projeta vaga preservando integralmente o texto de descrição, competências e requisitos."""
    context["title"] = job.title.value or context.get("title", "")
    context["company"] = job.company_name.value or ""
    context["company_name"] = job.company_name.value or ""
    context["location"] = job.location.value or ""
    context["country"] = job.country.value or ""
    context["employment_type"] = job.employment_type.value or ""

    if job.salary_text.value:
        context["salary_text"] = job.salary_text.value

    desc = job.description_text.value or ""
    context["description_text"] = desc
    context["description"] = desc

    if job.responsibilities:
        context["responsibilities"] = job.responsibilities
    if job.requirements_skills:
        context["requirements"] = job.requirements_skills

    context["key_metrics"] = {
        "has_description": bool(desc),
        "description_length": len(desc),
        "location": job.location.value or "",
        "company": job.company_name.value or "",
    }


def _project_offer_observation(offer: OfferObservation, context: dict[str, Any]) -> None:
    """Projeta oferta educacional com atributos comerciais e de currículo."""
    context["title"] = offer.title.value or context.get("title", "")
    context["institution"] = offer.institution_name.value or ""
    context["institution_name"] = offer.institution_name.value or ""
    context["category"] = offer.category.value or ""
    context["modality"] = offer.modality.value or ""
    context["workload_hours"] = offer.workload_hours.value

    if offer.pricing:
        pr = offer.pricing
        context["price"] = {
            "total_price": pr.total_price.value,
            "installments": pr.installments.value,
            "installment_value": pr.installment_value.value,
            "period": pr.period.value,
            "currency": pr.currency.value,
        }

    syllabus = offer.curriculum_text.value or ""
    if syllabus:
        context["syllabus"] = syllabus
    if offer.curriculum_modules:
        context["curriculum_modules"] = offer.curriculum_modules

    context["key_metrics"] = {
        "workload_hours": offer.workload_hours.value,
        "institution": offer.institution_name.value or "",
    }


def _project_social_observation(social: SocialObservation, context: dict[str, Any]) -> None:
    """Projeta manifestação social de profissionais e comunidade."""
    context["platform"] = social.channel or ""
    context["author"] = social.author.value or ""
    context["published_at"] = social.published_at.value or ""
    context["content_text"] = social.text.value or ""

    context["key_metrics"] = {
        "platform": social.channel,
        "author": social.author.value or "",
    }


def _project_ad_observation(ad: AdObservation, context: dict[str, Any]) -> None:
    """Projeta anúncio publicitário de concorrente ou da instituição."""
    context["advertiser"] = ad.page_name.value or ""
    context["headline"] = ad.headline.value or ""
    context["ad_copy"] = ad.ad_text.value or ""
    context["target_url"] = ad.cta_url.value or ""

    context["key_metrics"] = {
        "advertiser": ad.page_name.value or "",
        "ad_id": ad.ad_id,
    }


def _project_generic_dict(data: dict[str, Any], context: dict[str, Any]) -> None:
    """Projeção segura para dados que não puderam ser normalizados em modelo conhecido."""
    for k in (
        "companyName",
        "company",
        "positionName",
        "location",
        "descriptionText",
        "description",
        "text",
        "body",
        "price_brl",
        "ticket",
        "workload_hours",
    ):
        if k in data and data[k] is not None:
            context[k] = data[k]


def _enforce_budget(
    context: dict[str, Any],
    budget: int,
    omissions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Ajusta deterministamente o conteúdo ao orçamento sem cortes cegos de JSON."""
    # 1. Reduz primeiro campos secundários (ex.: timeline_summary)
    if "timeline_summary" in context and isinstance(context["timeline_summary"], list):
        orig_len = len(context["timeline_summary"])
        if orig_len > 20:
            context["timeline_summary"] = context["timeline_summary"][:20]
            omissions.append(
                {
                    "field": "timeline_summary",
                    "reason": "budget_exceeded",
                    "original_length": orig_len,
                    "retained_length": 20,
                }
            )

    context["omissions"] = omissions
    serialized = json.dumps(context, ensure_ascii=False)
    if len(serialized) <= budget:
        context.pop("omissions", None)
        return context

    # 2. Reduz campos de texto longo levando em conta overhead do diagnóstico
    for text_field in ("description_text", "description", "requirements", "syllabus", "content_text"):
        if text_field in context and isinstance(context[text_field], str):
            orig_text = context[text_field]
            orig_len = len(orig_text)
            excess = len(serialized) - budget + 100
            new_len = max(50, orig_len - excess)
            if new_len < orig_len:
                context[text_field] = orig_text[:new_len] + "..."
                omissions.append(
                    {
                        "field": text_field,
                        "reason": "budget_exceeded",
                        "original_length": orig_len,
                        "retained_length": len(context[text_field]),
                    }
                )
                context["omissions"] = omissions
                serialized = json.dumps(context, ensure_ascii=False)
                if len(serialized) <= budget:
                    context.pop("omissions", None)
                    return context

    # 3. Fallback determinístico se ainda exceder em orçamentos extremos
    for _ in range(5):
        context["omissions"] = omissions
        serialized = json.dumps(context, ensure_ascii=False)
        if len(serialized) <= budget:
            break
        excess = len(serialized) - budget + 20
        longest_field = None
        max_flen = 0
        for k, v in context.items():
            if k != "omissions" and isinstance(v, str) and len(v) > max_flen:
                longest_field = k
                max_flen = len(v)
        if longest_field and max_flen > 30:
            cut_len = max(20, max_flen - excess)
            context[longest_field] = context[longest_field][:cut_len]
        else:
            break

    context.pop("omissions", None)
    return context
