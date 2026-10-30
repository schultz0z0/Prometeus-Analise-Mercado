"""Resumo observável por consulta; sucesso técnico não implica suporte analítico."""

from collections import Counter
from typing import Any


def summarize_collection(
    runs: list[dict[str, Any]], evidences: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    report = []
    for run in runs:
        items = [e for e in evidences if e.get("tool_run_id") == run["id"]]
        qualifications = [
            (e.get("sanitized_data") or {}).get("_qualification") or {} for e in items
        ]
        accepted = sum(q.get("accepted") is True for q in qualifications)
        context = sum(q.get("context_only") is True for q in qualifications)
        status = run.get("status")
        parameters = run.get("parameters") or {}
        observation = parameters.get("observation_status")
        reasons = Counter(str(q["reason"])[:250] for q in qualifications if q.get("reason"))
        reasons.update(
            str(item["reason"])[:250]
            for item in parameters.get("rejected_items", [])
            if isinstance(item, dict) and item.get("reason")
        )
        outcome = (
            "partial_execution"
            if status == "PARTIAL"
            else "execution_failed"
            if status == "FAILED"
            else "rejected_content"
            if observation == "rejected_items"
            else "empty_dataset"
            if status == "EMPTY"
            else "qualified_sample"
            if accepted
            else "context_only"
            if context
            else "no_qualified_evidence"
        )
        report.append(
            {
                "call_id": run.get("planned_call_id"),
                "capability": run["capability"],
                "query": str(run.get("query") or "")[:500],
                "status": status,
                "raw_records": run.get("raw_items_count", 0),
                "normalized_records": run.get("valid_items_count", 0),
                "qualified_records": accepted,
                "context_records": context,
                "rejected_records": parameters.get("rejected_items_count", 0),
                "observation_status": observation,
                "outcome": outcome,
                "error_code": run.get("error_code"),
                "sample_scope": parameters.get("sample_scope", "capped_sample"),
                "sampling": parameters.get("sampling"),
                "entities": parameters.get("entities"),
                "url_outcomes": parameters.get("url_outcomes"),
                "reasons": dict(reasons),
            }
        )
    return report
