"""Preços por oferta: totais observáveis, categoria e origem explícitas."""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime
from decimal import Decimal
from statistics import mean, stdev
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def _plain(value: str) -> str:
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()


AMOUNT = r"(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:,\d{1,2})?)"


def _amount(value: str) -> Decimal:
    return Decimal(value.replace(".", "").replace(",", "."))


def _fee_condition(text: str, start: int) -> bool:
    prefix = re.split(r"[.!?;\n]", text[max(0, start - 100) : start])[-1]
    fees = list(re.finditer(r"\b(?:taxa|matricula|inscricao|material)\b", prefix))
    tuition = list(re.finditer(r"\b(?:curso|investimento|mensalidade)\b", prefix))
    return bool(fees and (not tuition or fees[-1].start() > tuition[-1].start()))


def extract_price_conditions(text: str) -> list[dict[str, Any]]:
    """Só calcula total com número explícito de parcelas ou total publicado."""
    normalized = _plain(text)
    found: list[dict[str, Any]] = []
    patterns = [
        rf"\b(\d{{1,3}})\s*(?:x|parcelas?(?:\s+mensais)?)\s*(?:de\s*)?(?:r\$|brl)\s*{AMOUNT}",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, normalized):
            if _fee_condition(normalized, match.start()):
                continue
            count = int(match.group(1))
            if 1 <= count <= 120 and _amount(match.group(2)) > 0:
                total = (_amount(match.group(2)) * count).quantize(Decimal(".01"))
                found.append(
                    {
                        "total_brl": float(total),
                        "installments": count,
                        "installment_brl": float(_amount(match.group(2))),
                        "condition": "parcelado",
                        "quote": text[max(0, match.start() - 30) : match.end() + 50],
                    }
                )
    for pattern in [
        rf"(?:investimento\s+total|valor\s+total|valor\s+[aà]\s+vista|[aà]\s+vista)\s*[:\-]?\s*(?:r\$|brl)\s*{AMOUNT}",
        rf"(?:r\$|brl)\s*{AMOUNT}\s*(?:[aà]\s+vista|no\s+total)",
    ]:
        for match in re.finditer(pattern, normalized):
            if _fee_condition(normalized, match.start()):
                continue
            value = _amount(match.group(1))
            if value > 0:
                found.append(
                    {
                        "total_brl": float(value),
                        "installments": 1,
                        "condition": "total_publicado",
                        "quote": text[max(0, match.start() - 30) : match.end() + 50],
                    }
                )
    unique: dict[tuple[float, int], dict[str, Any]] = {}
    for condition in found:
        unique[(condition["total_brl"], condition["installments"])] = condition
    return list(unique.values())


def _category(value: str) -> str | None:
    text = _plain(value)
    if re.search(r"\bmba\b", text):
        return "mba"
    if re.search(r"\bpos\b|especializa", text):
        return "pos"
    if "extens" in text:
        return "extensao"
    if "graduacao" in text:
        return "graduacao"
    return None


def _same_theme(title: str, target: str) -> bool:
    stop = {
        "curso",
        "gestao",
        "avancada",
        "executivo",
        "mba",
        "pos",
        "graduacao",
        "especializacao",
        "para",
        "com",
        "dos",
        "das",
        "ead",
        "online",
    }

    def tokens(value: str) -> set[str]:
        return {
            w.rstrip("s")
            for w in re.findall(r"[a-z]+", _plain(value))
            if len(w) > 3 and w not in stop
        }

    return bool(tokens(title) & tokens(target))


TRACKING_QUERY_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "gclsrc",
    "dclid",
    "zanpid",
    "msclkid",
    "_ga",
    "_gl",
    "_ke",
    "mc_cid",
    "mc_eid",
}


def _canonical(url: str) -> str:
    p = urlsplit(url)
    filtered_query = []
    if p.query:
        for k, v in parse_qsl(p.query, keep_blank_values=False):
            if k.lower() not in TRACKING_QUERY_PARAMS and not k.lower().startswith("utm_"):
                filtered_query.append((k, v))
    filtered_query.sort()
    query_str = urlencode(filtered_query) if filtered_query else ""
    return urlunsplit(
        ("https", (p.hostname or "").lower().removeprefix("www."), p.path.rstrip("/"), query_str, "")
    )


def build_price_reference(
    *,
    course_title: str,
    level: str,
    institution_name: str,
    internal_prices: list[dict[str, Any]],
    offers: list[dict[str, Any]],
    installments: int | None = None,
    institution_domains: list[str] | None = None,
) -> dict[str, Any]:
    """Cada curso contribui uma vez com um total inequivocamente observado.

    Um valor sem prazo não se torna total. A referência não estima margem.
    """
    comparables: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    seen: set[str] = set()
    expected = _category(level) or _category(course_title)
    own_domains = {x.lower().removeprefix("www.") for x in institution_domains or []}
    if "ens" == _plain(institution_name).strip() or "escola de negocios e seguros" in _plain(
        institution_name
    ):
        own_domains.update({"ens.edu.br", "enscursos.com.br"})
    for item in internal_prices:
        title = str(item.get("name") or "")
        if _category(str(item.get("category") or title)) != expected or not _same_theme(
            title, course_title
        ):
            excluded.append(
                {
                    "id": item.get("course_id"),
                    "origin": "internal",
                    "reason_code": "category_or_theme_mismatch",
                }
            )
            continue
        value = item.get("total_brl")
        key = "internal:" + str(item.get("course_id"))
        if (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and value > 0
            and key not in seen
        ):
            comparables.append(
                {
                    **item,
                    "origin": "internal",
                    "total_brl": round(float(value), 2),
                    "evidence_ids": item.get("evidence_ids", [item.get("course_id")]),
                }
            )
            seen.add(key)
    for item in offers:
        data = item.get("sanitized_data") or {}
        title = str(item.get("title") or "")
        url = str(item.get("source_url") or "")
        host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
        qualification = data.get("_qualification") or {}
        reason = None
        if qualification.get("own_institution") or any(
            host == domain or host.endswith("." + domain) for domain in own_domains
        ):
            reason = "own_institution"
        elif qualification.get("accepted") is not True:
            reason = "not_qualified"
        elif not expected or _category(title) != expected:
            reason = "category_mismatch"
        elif not _same_theme(title, course_title):
            reason = "theme_mismatch"
        if reason:
            excluded.append({"id": item.get("id"), "origin": "external", "reason_code": reason})
            continue
        key = _canonical(url)
        if not host:
            continue
        if key in seen:
            continue
        # Prefer the longest original page representation, never add duplicated copies.
        text = max((str(data.get(k) or "") for k in ("markdown", "text", "description")), key=len)
        # Related-course footers have a different subject and cannot supply
        # prices for the page's main offer.
        boundary = re.search(
            r"outros cursos|cursos relacionados|veja tambem|voce tambem pode|recomendados para voce",
            _plain(text),
        )
        if boundary:
            text = text[: boundary.start()]
        conditions = extract_price_conditions(text)
        # Historical news is not proof of a current commercial price.
        dates = re.findall(
            r"\b(?:19|20)\d{2}\b", str(data.get("publishedAt") or data.get("date") or "")
        )
        if dates and int(dates[0]) < datetime.now(UTC).year:
            excluded.append(
                {
                    "id": item.get("id"),
                    "origin": "external",
                    "reason_code": "dated_offer_requires_current_confirmation",
                }
            )
            continue
        if not conditions:
            excluded.append(
                {"id": item.get("id"), "origin": "external", "reason_code": "total_not_observed"}
            )
            continue
        # Matching a payment term does not link an amount to a course. A
        # multi-price page needs attribution by offer before any total is used.
        if len({c["total_brl"] for c in conditions}) > 1:
            excluded.append(
                {
                    "id": item.get("id"),
                    "origin": "external",
                    "reason_code": "ambiguous_payment_condition",
                }
            )
            continue
        if installments:
            nearest = min(abs(c["installments"] - installments) for c in conditions)
            candidates = [c for c in conditions if abs(c["installments"] - installments) == nearest]
            if len({c["total_brl"] for c in candidates}) > 1:
                excluded.append(
                    {
                        "id": item.get("id"),
                        "origin": "external",
                        "reason_code": "ambiguous_payment_condition",
                    }
                )
                continue
            selected = candidates[0]
        else:
            totals = {c["total_brl"] for c in conditions}
            if len(totals) > 1:
                excluded.append(
                    {
                        "id": item.get("id"),
                        "origin": "external",
                        "reason_code": "ambiguous_payment_condition",
                    }
                )
                continue
            selected = conditions[0]
        comparables.append(
            {
                "course_id": key,
                "name": title,
                "category": expected,
                "origin": "external",
                "evidence_ids": [item["id"]],
                "source_url": url,
                **selected,
                "conditions_observed": conditions,
            }
        )
        seen.add(key)
    internal = [c["total_brl"] for c in comparables if c["origin"] == "internal"]
    external = [c["total_brl"] for c in comparables if c["origin"] == "external"]
    all_totals = [c["total_brl"] for c in comparables]
    internal_mean = round(mean(internal), 2) if internal else None
    external_mean = round(mean(external), 2) if external else None
    dispersion = round(stdev(all_totals), 2) if len(all_totals) >= 2 else 0.0
    price_gap = (
        round(abs(internal_mean - external_mean), 2)
        if (internal_mean is not None and external_mean is not None)
        else None
    )
    return {
        "method": "arithmetic_mean_per_comparable_course",
        "mean_total_brl": round(mean(all_totals), 2) if all_totals else None,
        "internal_mean_brl": internal_mean,
        "external_mean_brl": external_mean,
        "dispersion_total_brl": dispersion,
        "price_gap_brl": price_gap,
        "internal_count": len(internal),
        "external_count": len(external),
        "comparables": comparables,
        "excluded": excluded,
        "limitations": (["Sem preço interno comparável."] if not internal else [])
        + (["Sem preço externo comparável."] if not external else []),
        "currency": "BRL",
        "price_period": "total",
    }
