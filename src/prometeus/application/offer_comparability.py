"""Observed course identity and category; never infer from institution or hours."""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit

from prometeus.application.pricing_reference import _category, _plain, _same_theme
from prometeus.domain.research import CourseUnderstanding


def _course_category(value: str) -> str | None:
    known = _category(value)
    if known:
        return known
    value = _plain(value).replace("_", " ")
    if any(term in value for term in ("curso livre", "curta duracao", "workshop", "treinamento", "capacitacao")):
        return "curso_livre"
    if "certificacao" in value:
        return "certificacao"
    return None


def classify_competitor_offer(
    *, evidence_type: str, title: str, source_url: str, data: dict[str, Any],
    understanding: CourseUnderstanding, relevant: bool, own: bool, sector: bool,
    contextual: bool = False,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "is_offer": False, "relation": "not_qualified", "observed_category": None,
        "proposed_category": _course_category(understanding.level) or _course_category(understanding.course_title),
        "reason": "Oferta educacional externa pertinente ainda não confirmada", "missing_fields": [],
    }
    if evidence_type not in {"OFFER", "PAID_COMPETITION"} or not (relevant or contextual) or own or sector:
        return result
    try:
        url = urlsplit(source_url)
    except ValueError:
        return result
    if re.search(r"/(?:noticias?|posts?|blog|artigos?|news)(?:/|$)", url.path, re.I) or url.hostname and url.hostname.startswith("blog."):
        result["reason"] = "Notícia ou artigo não confirma uma oferta de curso"
        return result
    observed_title = next((data[key].strip() for key in ("course_name", "pageTitle", "title") if isinstance(data.get(key), str) and data[key].strip()), title.strip())
    if not observed_title or _plain(observed_title) in {"product", "produto", "home", "inicio"}:
        result["missing_fields"] = ["course_identity"]
        return result
    explicit_category = next((data[key] for key in ("course_type", "category", "level") if isinstance(data.get(key), str) and data[key].strip()), "")
    observed_category = _course_category(explicit_category) or _course_category(observed_title)
    course_path = bool(re.search(r"/(?:cursos?|produto|mba|pos|pos-graduacao|especializacao|extensao|formacao|treinamentos?)(?:/|$|-)", _plain(url.path)))
    identity = bool(isinstance(data.get("course_name"), str) and data["course_name"].strip()) or course_path or bool(observed_category and any(data.get(k) for k in ("syllabus", "curriculum_modules", "enrollment_url")))
    if not identity:
        result["missing_fields"] = ["course_identity"]
        return result
    if contextual and not relevant and not (
        observed_category and result["proposed_category"]
        and observed_category != result["proposed_category"]
        and _same_theme(observed_title, understanding.course_title)
    ):
        result["reason"] = "Contexto sem comparabilidade temática e categoria adjacente confirmadas"
        return result
    result.update(is_offer=True, observed_category=observed_category)
    missing = [key for key in ("observed_category", "proposed_category") if not result[key]]
    if missing:
        result.update(relation="unclassified", reason="Oferta observada; relação direta ou adjacente ainda não confirmada", missing_fields=missing)
    elif observed_category == result["proposed_category"]:
        result.update(relation="direct", reason="Oferta pertinente com a mesma categoria educacional observada")
    else:
        result.update(relation="adjacent", reason="Oferta pertinente de categoria educacional diferente da proposta")
    return result


def qualified_competitor_offer(qualification: dict[str, Any], evidence_type: str) -> bool:
    """Shared admission for facts and recovery; contextual news never counts."""
    return bool(
        evidence_type in {"OFFER", "PAID_COMPETITION"}
        and qualification.get("accepted") is True
        and qualification.get("context_only") is not True
        and qualification.get("own_institution") is not True
        and qualification.get("actor_role") != "sector_radar"
        and (qualification.get("offer_comparability") or {}).get("is_offer") is True
    )
