"""Funil auditável de coleta, finalidade e perdas — sem promover rejeições."""

from __future__ import annotations

from typing import Any


def summarize_evidence(rows: list[dict[str, Any]], *, used_ids: set[str]) -> dict[str, Any]:
    sources: dict[str, Any] = {}
    for row in rows:
        name = str(row["source_name"])
        source = sources.setdefault(
            name,
            {
                "collected_records": 0,
                "accepted_records": 0,
                "context_records": 0,
                "excluded_records": 0,
                "used_in_score_records": 0,
                "reasons": {},
                "use_for": {},
            },
        )
        source["collected_records"] += 1
        q = (row.get("sanitized_data") or {}).get("_qualification") or {}
        accepted = q.get("accepted") is True
        context = q.get("context_only") is True
        state = (
            "accepted_records" if accepted else "context_records" if context else "excluded_records"
        )
        source[state] += 1
        if str(row["id"]) in used_ids:
            source["used_in_score_records"] += 1
        if not accepted:
            reason = str(q.get("reason") or "Sem qualificação registrada")
            source["reasons"][reason] = source["reasons"].get(reason, 0) + 1
        for purpose in q.get("use_for", []):
            source["use_for"][purpose] = source["use_for"].get(purpose, 0) + 1
    totals = {
        key: sum(source[key] for source in sources.values())
        for key in (
            "collected_records",
            "accepted_records",
            "context_records",
            "excluded_records",
            "used_in_score_records",
        )
    }
    return {
        **totals,
        "sources": sources,
        "record_semantics": "Registros coletados; não representam tamanho total do mercado. Capturas repetidas podem sustentar a mesma entidade.",
    }
