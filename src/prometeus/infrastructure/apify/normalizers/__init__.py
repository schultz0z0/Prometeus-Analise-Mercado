"""Normalizadores canônicos para dados brutos do Apify (Tarefa 1.1).

Converte payloads heterogêneos de diferentes Actors e builds em observações
tipadas com proveniência e tratamento de variantes de schema.
"""

from __future__ import annotations

import html
import re
from typing import Any

from prometeus.domain.evidence_observations import (
    AdObservation,
    BaseObservation,
    JobObservation,
    ObservationField,
    OfferObservation,
    PageAcquisition,
    PriceObservation,
    SocialObservation,
    TrendSeries,
    TrendSeriesPoint,
)

TAG_RE = re.compile(r"<[^>]+>")
HOURS_RE = re.compile(r"\b(\d{2,4})\s*(?:h|horas?|hrs?)\b", re.IGNORECASE)


def _clean_html(text: str) -> str:
    cleaned = TAG_RE.sub(" ", text)
    return re.sub(r"\s+", " ", html.unescape(cleaned)).strip()


def normalize_trends(
    raw: dict[str, Any], source_url: str = "", *, url: str = ""
) -> TrendSeries:
    """Normaliza séries do Google Trends tratando variantes de lista/escalar em isPartial e hasData."""
    effective_url = url or source_url
    term = str(raw.get("term") or raw.get("query") or "termo_pesquisado")
    raw_points = (
        raw.get("interestOverTime_timelineData")
        or raw.get("timelineData")
        or raw.get("points")
        or []
    )
    if not isinstance(raw_points, list):
        raw_points = []

    points: list[TrendSeriesPoint] = []
    for _idx, p in enumerate(raw_points):
        if not isinstance(p, dict):
            continue
        # Preserva o valor exato original de time como string, sem redação indevida
        raw_time = str(p.get("time", ""))
        fmt_time = p.get("formattedTime") or p.get("formattedAxisTime")

        val_list = p.get("value", [])
        if isinstance(val_list, (int, float)):
            val_list = [val_list]
        elif not isinstance(val_list, list):
            val_list = []

        # Tratamento da variante isPartial escalar vs lista: isPartial=[true] ou isPartial=true
        is_partial_raw = p.get("isPartial", False)
        if isinstance(is_partial_raw, list):
            is_partial = bool(is_partial_raw[0]) if is_partial_raw else False
        else:
            is_partial = bool(is_partial_raw)

        # Tratamento da variante hasData escalar vs lista
        has_data_raw = p.get("hasData")
        if isinstance(has_data_raw, list):
            has_data: bool | None = bool(has_data_raw[0]) if has_data_raw else None
        elif isinstance(has_data_raw, bool):
            has_data = has_data_raw
        else:
            has_data = None

        points.append(
            TrendSeriesPoint(
                time=raw_time,
                formatted_time=str(fmt_time) if fmt_time else None,
                value=val_list,
                is_partial=is_partial,
                has_data=has_data,
            )
        )

    positives = sum(
        1 for pt in points if any(isinstance(v, (int, float)) and v > 0 for v in pt.value)
    )
    partials = sum(1 for pt in points if pt.is_partial)
    valids = sum(1 for pt in points if pt.value)
    all_values = [v for pt in points for v in pt.value if isinstance(v, (int, float))]
    avg_interest = round(sum(all_values) / max(len(points), 1), 2) if all_values else 0.0

    return TrendSeries(
        source_name="apify_google_trends",
        source_url=effective_url or "https://trends.google.com",
        term=term,
        points=points,
        total_points=len(points),
        valid_points=valids,
        positive_points=positives,
        partial_points=partials,
        average_interest=avg_interest,
        growth_trend_pct=0.0,
        raw_payload=raw,
    )


def normalize_job(
    raw: dict[str, Any], source_url: str = "", *, url: str = ""
) -> JobObservation:
    """Normaliza vagas do LinkedIn ou Indeed extraindo descrições completas e competências."""
    effective_url = url or source_url
    title = raw.get("title") or raw.get("jobTitle") or ""
    company = raw.get("companyName") or raw.get("company") or ""
    location = raw.get("location") or raw.get("jobLocation") or ""

    desc_text = raw.get("descriptionText") or raw.get("description")
    if not desc_text and raw.get("descriptionHtml"):
        desc_text = _clean_html(str(raw["descriptionHtml"]))
    desc_str = str(desc_text).strip() if desc_text else ""

    skills_raw = raw.get("skills") or raw.get("requirements") or []
    if isinstance(skills_raw, str):
        skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
    elif isinstance(skills_raw, list):
        skills = [str(s).strip() for s in skills_raw if str(s).strip()]
    else:
        skills = []

    salary = raw.get("salary") or raw.get("salaryText") or ""

    return JobObservation(
        source_name="apify_linkedin_jobs",
        source_url=effective_url or str(raw.get("jobUrl") or raw.get("url") or ""),
        title=ObservationField.observed(str(title), pointer="/title")
        if title
        else ObservationField.missing(pointer="/title"),
        company_name=ObservationField.observed(str(company), pointer="/companyName")
        if company
        else ObservationField.missing(pointer="/companyName"),
        location=ObservationField.observed(str(location), pointer="/location")
        if location
        else ObservationField.missing(pointer="/location"),
        country=ObservationField.missing(pointer="/country"),
        description_text=ObservationField.observed(desc_str, pointer="/descriptionText")
        if desc_str
        else ObservationField.missing(pointer="/descriptionText"),
        requirements_skills=skills,
        salary_text=ObservationField.observed(str(salary), pointer="/salary")
        if salary
        else ObservationField.missing(pointer="/salary"),
        raw_payload=raw,
    )


def normalize_crawler_page(
    raw: dict[str, Any], source_url: str = "", *, url: str = ""
) -> OfferObservation | PageAcquisition:
    """Normaliza páginas coletadas por crawler ou search, separando desfechos de falha."""
    effective_url = url or source_url or str(raw.get("url") or "")
    status_code = raw.get("httpStatusCode") or raw.get("statusCode")
    if isinstance(status_code, int) and status_code >= 400:
        outcome = (
            "not_found"
            if status_code == 404
            else "blocked"
            if status_code in {401, 403}
            else "extraction_failed"
        )
        return PageAcquisition(
            source_name="apify_web_crawler",
            source_url=effective_url,
            status_code=status_code,
            outcome=outcome,
            title=raw.get("pageTitle") or raw.get("title"),
            raw_payload=raw,
        )

    title = raw.get("pageTitle") or raw.get("title") or ""
    text_content = raw.get("text") or raw.get("content") or ""

    # Extração de carga horária se informada
    hours = None
    if raw.get("workload_hours"):
        try:
            hours = int(raw["workload_hours"])
        except (ValueError, TypeError):
            pass
    elif text_content:
        match = HOURS_RE.search(text_content)
        if match:
            hours = int(match.group(1))

    # Preço estruturado
    price_obs = None
    pricing_data = raw.get("pricing")
    if isinstance(pricing_data, dict):
        installments = pricing_data.get("installments")
        inst_val = pricing_data.get("installment_value")
        currency = pricing_data.get("currency")
        total = pricing_data.get("total_price")
        if total is None and installments and inst_val:
            try:
                total = float(installments) * float(inst_val)
            except (ValueError, TypeError):
                total = None
        price_obs = PriceObservation(
            total_price=ObservationField.observed(float(total), pointer="/pricing/total_price")
            if total is not None
            else ObservationField.missing(pointer="/pricing/total_price"),
            installments=ObservationField.observed(int(installments), pointer="/pricing/installments")
            if installments is not None
            else ObservationField.missing(pointer="/pricing/installments"),
            installment_value=ObservationField.observed(float(inst_val), pointer="/pricing/installment_value")
            if inst_val is not None
            else ObservationField.missing(pointer="/pricing/installment_value"),
            currency=ObservationField.observed(str(currency), pointer="/pricing/currency")
            if currency
            else ObservationField.missing(pointer="/pricing/currency"),
        )

    return OfferObservation(
        source_name="apify_web_crawler",
        source_url=effective_url,
        title=ObservationField.observed(str(title), pointer="/pageTitle")
        if title
        else ObservationField.missing(pointer="/pageTitle"),
        workload_hours=ObservationField.observed(hours, pointer="/workload_hours", unit="h")
        if hours is not None
        else ObservationField.missing(pointer="/workload_hours"),
        pricing=price_obs,
        raw_payload=raw,
    )


def normalize_ad(
    raw: dict[str, Any], source_url: str = "", *, url: str = ""
) -> AdObservation:
    """Normaliza anúncios da Meta Ads Library."""
    effective_url = url or source_url
    ad_id = str(raw.get("adArchiveId") or raw.get("ad_id") or raw.get("id") or "")
    page_name = raw.get("pageName") or raw.get("page_name") or ""
    text = raw.get("text") or raw.get("ad_creative_body") or ""
    headline = raw.get("headline") or raw.get("ad_creative_link_title") or ""
    cta_url = raw.get("cta_url") or raw.get("link_url") or ""

    return AdObservation(
        source_name="apify_meta_ads_library",
        source_url=effective_url or f"https://www.facebook.com/ads/library/?id={ad_id}",
        ad_id=ad_id,
        page_name=ObservationField.observed(str(page_name), pointer="/pageName")
        if page_name
        else ObservationField.missing(pointer="/pageName"),
        headline=ObservationField.observed(str(headline), pointer="/headline")
        if headline
        else ObservationField.missing(pointer="/headline"),
        ad_text=ObservationField.observed(str(text), pointer="/text")
        if text
        else ObservationField.missing(pointer="/text"),
        cta_url=ObservationField.observed(str(cta_url), pointer="/cta_url")
        if cta_url
        else ObservationField.missing(pointer="/cta_url"),
        raw_payload=raw,
    )


def normalize_social(
    raw: dict[str, Any], source_url: str = "", *, url: str = ""
) -> SocialObservation:
    """Normaliza comentários de YouTube ou TikTok."""
    effective_url = url or source_url
    channel = "youtube" if "youtube" in effective_url.lower() or "commentText" in raw else "tiktok"
    post_id = str(raw.get("commentId") or raw.get("cid") or raw.get("id") or "")
    author = raw.get("author") or raw.get("authorName") or ""
    text = raw.get("commentText") or raw.get("text") or ""
    published = raw.get("publishedAt") or raw.get("createTime") or ""

    return SocialObservation(
        source_name=f"apify_{channel}",
        source_url=effective_url,
        channel=channel,
        post_id=post_id,
        author=ObservationField.observed(str(author), pointer="/author")
        if author
        else ObservationField.missing(pointer="/author"),
        text=ObservationField.observed(str(text), pointer="/text")
        if text
        else ObservationField.missing(pointer="/text"),
        published_at=ObservationField.observed(str(published), pointer="/publishedAt")
        if published
        else ObservationField.missing(pointer="/publishedAt"),
        raw_payload=raw,
    )


def normalize_observation(
    raw_or_name: Any,
    source_name_or_raw: Any = None,
    source_url: str = "",
    *,
    url: str = "",
) -> BaseObservation:
    """Despacha a normalização aceitando (raw, name) ou (name, raw) e url/source_url."""
    effective_url = url or source_url
    if isinstance(raw_or_name, str) and isinstance(source_name_or_raw, dict):
        source_name = raw_or_name
        raw = source_name_or_raw
    elif isinstance(raw_or_name, dict):
        raw = raw_or_name
        source_name = str(source_name_or_raw or "")
    else:
        raw = raw_or_name or {}
        source_name = str(source_name_or_raw or "")

    s = (source_name or "").lower()
    if "trend" in s:
        return normalize_trends(raw, source_url=effective_url)
    elif "job" in s or "linkedin" in s or "work" in s:
        return normalize_job(raw, source_url=effective_url)
    elif "meta" in s or "ad" in s or "paid_competition" in s:
        return normalize_ad(raw, source_url=effective_url)
    elif "youtube" in s or "tiktok" in s or "social" in s:
        return normalize_social(raw, source_url=effective_url)
    else:
        return normalize_crawler_page(raw, source_url=effective_url)
