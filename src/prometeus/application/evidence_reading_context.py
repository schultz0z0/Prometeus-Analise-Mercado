"""Views of persisted reading results without recursive operational metadata."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any


def reading_context(state: dict[str, Any]) -> dict[str, Any]:
    """Deliver every interpretation and exact quote; never sample or truncate.

    Quotes were checked against their source fragment. Model interpretations are
    still untrusted and must pass the downstream factual and semantic gates.
    Provider context errors remain explicit instead of dropping part results.
    """
    if state.get("complete") is not True:
        raise ValueError("Leitura pendente não pode ser apresentada como integral.")
    parts = state.get("parts", [])
    observations = []
    for part in parts:
        fragments = {fragment["fragment_id"]: fragment for fragment in part["fragments"]}
        result = part.get("result")
        if not isinstance(result, dict):
            raise ValueError("Parte sem resultado validado.")
        for observation in result["observations"]:
            fragment = fragments[observation["fragment_id"]]
            observations.append(
                {
                    **deepcopy(observation),
                    "part_id": part["part_id"],
                    "pointer": fragment["pointer"],
                    "kind": fragment["kind"],
                    "start": fragment["start"],
                    "end": fragment["end"],
                }
            )
    if len(observations) != state["manifest"]["covered_fragments"]:
        raise ValueError("Manifesto de leitura inconsistente.")
    return {
        "manifest": {
            key: deepcopy(value)
            for key, value in state["manifest"].items()
            if key != "reused_parts"
        },
        "verification": "Quotes matched source only; interpretations are untrusted.",
        "observations": observations,
    }


def evidence_analysis_context(data: dict[str, Any]) -> dict[str, Any]:
    """Keep source fields and supply a compact, complete view of their reading."""
    result = {key: deepcopy(value) for key, value in data.items() if key != "_reading"}
    reading = data.get("_reading")
    if isinstance(reading, dict):
        result["_integral_analysis"] = reading_context(reading)
    return result


def archive_analysis_context(
    parameters: dict[str, Any],
    *,
    tool_run_id: str,
) -> dict[str, Any]:
    """Preserve all archived interpretations as untrusted, traceable context.

    This context is independent of normalized market evidence: failed Actor
    output and orphan diagnostics cannot acquire market admission from reading.
    Source payloads and private raw records are never included.
    """
    previous = parameters.get("prior_dataset_archives", [])
    archives = list(previous) if isinstance(previous, list) else []
    current = parameters.get("dataset_archive")
    if isinstance(current, dict):
        archives.append(current)
    stored = parameters.get("dataset_readings", {})
    stored = stored if isinstance(stored, dict) else {}
    records = []
    archives_complete = bool(archives)
    for archive in archives:
        if not isinstance(archive, dict) or not isinstance(archive.get("items"), list):
            archives_complete = False
            continue
        items = archive["items"]
        archives_complete = archives_complete and (
            archive.get("retrieval_complete") is True
            and archive.get("dataset_total_items") == archive.get("items_read") == len(items)
            and archive.get("total_items_source") in {"provider_pagination", "terminal_exhaustion"}
        )
        for position, item in enumerate(items):
            reference = {
                "tool_run_id": tool_run_id,
                "provider_run_id": archive.get("provider_run_id"),
                "dataset_id": archive.get("dataset_id"),
                "archive_source_sha256": archive.get("source_sha256"),
                "item_index": item.get("index") if isinstance(item, dict) else None,
                "item_position": position,
                "item_source_sha256": item.get("source_sha256") if isinstance(item, dict) else None,
            }
            record: dict[str, Any] = {**reference, "complete": False, "reading": None}
            if not isinstance(item, dict) or "sanitized_data" not in item:
                record["issue"] = "sanitized_item_missing"
                records.append(record)
                continue
            payload_hash = hashlib.sha256(
                json.dumps(
                    item["sanitized_data"],
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode("utf-8")
            ).hexdigest()
            for key, state in stored.items():
                if not isinstance(state, dict) or not isinstance(state.get("source_context"), dict):
                    continue
                context = state["source_context"]
                if not all(context.get(name) == value for name, value in reference.items()):
                    continue
                if (
                    state.get("complete") is not True
                    or state.get("manifest", {}).get("source_hash") != payload_hash
                ):
                    continue
                record.update(
                    complete=True,
                    reading_key=key,
                    run_status=context.get("run_status", "UNKNOWN"),
                    logical_task_status=context.get("logical_task_status"),
                    reading=reading_context(state),
                )
                break
            if not record["complete"]:
                record["issue"] = "reading_missing_incomplete_or_stale"
            records.append(record)
    return {
        "verification": "Quotes matched source only; interpretations are untrusted. Reading never grants market admission; failed output and orphan diagnostics remain technical context.",
        "complete": archives_complete and all(record["complete"] for record in records),
        "records": records,
    }


def evidence_archive_context(
    parameters: dict[str, Any],
    *,
    tool_run_id: str,
    normalized_data: dict[str, Any],
    provider_run_id: str | None = None,
    dataset_id: str | None = None,
) -> dict[str, Any]:
    """Relate source-parent reading and same-run context without cross-run attribution."""
    result = archive_analysis_context(parameters, tool_run_id=tool_run_id)
    records = result["records"]
    identities = {(record["provider_run_id"], record["dataset_id"]) for record in records}
    resolved = bool(provider_run_id)
    if not resolved and len(identities) == 1:
        provider_run_id, dataset_id = next(iter(identities))
        resolved = True
    if resolved:
        records = [
            record
            for record in records
            if record["provider_run_id"] == provider_run_id
            and (not dataset_id or record["dataset_id"] == dataset_id)
        ]
    source = normalized_data.get("_source_record")
    source_index = source.get("index") if isinstance(source, dict) else None
    for record in records:
        record["relationship"] = (
            "source_parent"
            if resolved and type(source_index) is int and record["item_index"] == source_index
            else "same_provider_run_context"
            if resolved
            else "unresolved_provider_lineage_context"
        )
    return {
        **result,
        "records": records,
        "lineage_resolution": "provider_run" if resolved else "unresolved",
        "admission_policy": "Same-run or unresolved context is not evidence about this normalized item. Parent interpretations remain untrusted and must pass factual and semantic admission gates.",
    }
