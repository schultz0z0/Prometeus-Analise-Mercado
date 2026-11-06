"""Projeção factual da cobertura por instituição, independente de redação e scoring."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from prometeus.application.pricing_reference import TRACKING_QUERY_PARAMS


def _parameters(record: dict[str, Any]) -> dict[str, Any]:
    value = record.get("parameters")
    return value if isinstance(value, dict) else {}


def _single_target(record: dict[str, Any]) -> str | None:
    params = _parameters(record)
    target = params.get("competitor_id")
    if isinstance(target, str) and target:
        return target
    targets = params.get("competitor_ids")
    if isinstance(targets, list) and len(targets) == 1:
        return str(targets[0])
    # A multi-domain result cap may have been filled by only one institution.
    return None


def _phase(record: dict[str, Any]) -> str:
    phase = _parameters(record).get("collection_phase")
    if phase in {"discovery", "validation"}:
        return str(phase)
    return "validation" if record.get("capability") == "web_crawler" else "discovery"


def _success(run: dict[str, Any]) -> bool:
    return run.get("status") in {"SUCCEEDED", "EMPTY"}


def _observed(run: dict[str, Any]) -> bool:
    audit = _parameters(run)
    if audit.get("observation_status") == "budget_skipped":
        return False
    return bool(
        run.get("provider_run_id")
        or run.get("run_id")
        or audit.get("observation_status") in {"observed", "observed_empty", "rejected_items", "no_candidates_to_validate"}
    )


def _url_key(value: Any) -> str:
    if not isinstance(value, str) or not value:
        return ""
    try:
        url = urlsplit(value)
    except ValueError:
        return value
    query = urlencode(sorted(
        (key, value) for key, value in parse_qsl(url.query, keep_blank_values=True)
        if key.lower() not in TRACKING_QUERY_PARAMS | {"srsltid"}
        and not key.lower().startswith("utm_")
    ))
    return urlunsplit((url.scheme.lower(), url.netloc.lower(), url.path.rstrip("/"), query, ""))


def _url_failures(run: dict[str, Any]) -> list[dict[str, Any]]:
    """Uma oferta válida não oculta outras páginas que ficaram sem consulta útil.

    `not_found` é uma resposta terminal observada para aquela URL; bloqueio,
    extração inválida e truncamento continuam sendo lacunas operacionais.
    """
    outcomes = _parameters(run).get("url_outcomes")
    if not isinstance(outcomes, dict):
        return []
    return [
        {
            "run_id": run.get("id"),
            "planned_call_id": run.get("planned_call_id"),
            "source_url": url,
            "error_code": str(outcome),
            "error_message": f"Página sem validação concluída: {outcome}.",
        }
        for url, outcome in outcomes.items()
        if isinstance(url, str) and outcome not in {"fetched", "not_found"}
    ]


def _offers_for(competitor_id: str, offers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for offer in offers:
        if offer.get("competitor_id") != competitor_id:
            continue
        key = str(offer.get("canonical_entity_id") or _url_key(offer.get("source_url")))
        if not key:
            key = str(offer.get("evidence_id") or offer.get("title") or "")
        if not key:
            continue
        evidence_ids = [str(eid) for eid in offer.get("evidence_ids", []) if eid]
        if offer.get("evidence_id"):
            evidence_ids.append(str(offer["evidence_id"]))
        if key not in grouped:
            grouped[key] = {**offer, "evidence_ids": list(dict.fromkeys(evidence_ids))}
        else:
            existing = grouped[key]
            existing["evidence_ids"] = list(
                dict.fromkeys([*existing["evidence_ids"], *evidence_ids])
            )
            ranks = {"unclassified": 0, "adjacent": 1, "direct": 2}
            if ranks.get(str(offer.get("relation")), -1) > ranks.get(str(existing.get("relation")), -1):
                existing["relation"] = offer["relation"]
                if offer.get("relation_reason"):
                    existing["relation_reason"] = offer["relation_reason"]
            for field in ("price_display", "workload_hours", "modality", "collected_at"):
                if existing.get(field) in (None, "", "—") and offer.get(field) not in (None, "", "—"):
                    existing[field] = offer[field]
    return list(grouped.values())


def _row(
    competitor: dict[str, Any],
    calls: list[dict[str, Any]],
    runs: list[dict[str, Any]],
    offers: list[dict[str, Any]],
) -> dict[str, Any]:
    competitor_id = str(competitor["id"])
    targeted = [call for call in calls if _single_target(call) == competitor_id]
    by_id = {str(call["id"]): call for call in targeted if call.get("id")}
    related = [
        run
        for run in runs
        if str(run.get("planned_call_id") or "") in by_id
        or _single_target(run) == competitor_id
    ]
    discovery = [
        run for run in related if _phase(by_id.get(str(run.get("planned_call_id")), run)) == "discovery"
    ]
    validation = [run for run in related if run not in discovery]
    successful_searches = [run for run in discovery if _success(run) and _observed(run)]
    searched = bool(successful_searches)
    candidates = any(int(run.get("valid_items_count") or 0) > 0 for run in successful_searches)
    validation_calls = [call for call in targeted if _phase(call) == "validation"]
    validation_complete = bool(validation) and all(_success(run) and _observed(run) for run in validation)
    validation_complete = validation_complete and all(
        any(str(run.get("planned_call_id")) == str(call["id"]) for run in validation)
        for call in validation_calls
    )
    url_failures = [failure for run in related for failure in _url_failures(run)]
    validation_complete = validation_complete and not url_failures
    discovery_complete = searched and all(_success(run) for run in discovery)
    complete = discovery_complete and (not candidates or validation_complete) and not url_failures
    states = {str(run.get("status")) for run in related}
    audit_states = {
        str(_parameters(run).get("execution_status") or _parameters(run).get("authorization_status"))
        for run in related
    }
    if "IN_DOUBT" in states | audit_states or "in_doubt" in audit_states:
        execution = "in_doubt"
        complete = False
    elif states & {"RETRY_SCHEDULED", "RETRYING"} or any(
        _parameters(run).get("next_attempt_at") for run in related if not _success(run)
    ):
        execution = "retrying"
        complete = False
    elif states & {"RUNNING", "READY"}:
        execution = "running"
        complete = False
    elif complete:
        execution = "completed"
    elif searched:
        execution = "partial"
    elif states - {"PLANNED"}:
        execution = "blocked"
    else:
        execution = "not_started"

    confirmed = _offers_for(competitor_id, offers)
    if any(offer.get("relation") == "direct" for offer in confirmed):
        evidence_status = "direct_offer"
    elif any(offer.get("relation") == "adjacent" for offer in confirmed):
        evidence_status = "adjacent_offer"
    elif confirmed:
        evidence_status = "offer_relation_pending"
    elif candidates and not validation_complete:
        evidence_status = "validation_pending"
    elif complete:
        evidence_status = "no_qualified_offer"
    else:
        evidence_status = "not_observed"
    failures = [
        {
            "run_id": run.get("id"),
            "planned_call_id": run.get("planned_call_id"),
            "error_code": run.get("error_code") or _parameters(run).get("observation_status"),
            "error_message": str(run.get("error_message") or "")[:500],
        }
        for run in related
        if run.get("status") == "FAILED"
    ]
    failures.extend(url_failures)
    return {
        "competitor_id": competitor_id,
        "name": competitor.get("name") or competitor_id,
        "execution_status": execution,
        "evidence_status": evidence_status,
        "searched": searched,
        "complete": complete,
        "planned_call_ids": list(by_id),
        "run_ids": list(dict.fromkeys(str(run["id"]) for run in related if run.get("id"))),
        "failures": failures,
        "offers": confirmed,
        "evidence_ids": list(dict.fromkeys(eid for offer in confirmed for eid in offer["evidence_ids"])),
    }


def build_competitor_coverage(
    *,
    competitors: list[dict[str, Any]],
    calls: list[dict[str, Any]],
    runs: list[dict[str, Any]],
    offers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Projeta pesquisa executada e ofertas já qualificadas, sem analisar texto de query.

    O chamador fornece chamadas de todos os planos e evidências aprovadas pelo
    contrato de qualificação. Metadados explícitos vinculam tarefa e instituição.
    """
    rows = [_row(comp, calls, runs, offers or []) for comp in competitors if comp.get("id")]
    return {
        "schema_version": 1,
        "configured_total": len(rows),
        "searched_total": sum(row["searched"] for row in rows),
        "completed_total": sum(row["complete"] for row in rows),
        "blocked_total": sum(row["execution_status"] in {"blocked", "in_doubt"} for row in rows),
        "institutions_with_offers": sum(bool(row["offers"]) for row in rows),
        "total_offers": sum(len(row["offers"]) for row in rows),
        "coverage_complete": bool(rows) and all(row["complete"] for row in rows),
        "rows": rows,
    }
