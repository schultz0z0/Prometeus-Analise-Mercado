"""Public, content-free reconciliation of collection and persisted reader coverage."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _count(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _hash(value: Any) -> str | None:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        return None
    return hashlib.sha256(encoded).hexdigest()


def _reading_summary(state: Any, payload: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "complete": False,
        "status": "MISSING",
        "parts_total": 0,
        "parts_completed": 0,
        "fragments_total": 0,
        "fragments_covered": 0,
    }
    if not isinstance(state, dict):
        return summary
    summary["status"] = "INCOMPLETE"
    manifest = state.get("manifest")
    parts = state.get("parts")
    if not isinstance(manifest, dict) or not isinstance(parts, list):
        return summary
    summary["parts_total"] = len(parts)
    valid_structure = True
    part_ids = set()
    for part in parts:
        if not isinstance(part, dict) or not isinstance(part.get("fragments"), list):
            valid_structure = False
            continue
        part_id = part.get("part_id")
        if not isinstance(part_id, str) or part_id in part_ids:
            valid_structure = False
        else:
            part_ids.add(part_id)
        fragments = part["fragments"]
        summary["fragments_total"] += len(fragments)
        fragment_ids = [f.get("fragment_id") for f in fragments if isinstance(f, dict)]
        result = part.get("result")
        if not isinstance(result, dict) or result.get("part_id") != part_id:
            continue
        observations = result.get("observations")
        if not isinstance(observations, list):
            continue
        observed_ids = [o.get("fragment_id") for o in observations if isinstance(o, dict)]
        if (
            len(fragment_ids) == len(fragments) == len(set(fragment_ids))
            and all(isinstance(identifier, str) for identifier in fragment_ids)
            and len(observed_ids) == len(observations) == len(fragment_ids)
            and set(observed_ids) == set(fragment_ids)
        ):
            summary["parts_completed"] += 1
            summary["fragments_covered"] += len(fragments)
    source_hash = _hash(payload)
    source_matches = source_hash is not None and manifest.get("source_hash") == source_hash
    counts_match = all(
        manifest.get(field) == summary[public_field]
        for field, public_field in (
            ("total_parts", "parts_total"),
            ("completed_parts", "parts_completed"),
            ("total_fragments", "fragments_total"),
            ("covered_fragments", "fragments_covered"),
        )
    )
    complete = (
        state.get("version") == "integral-reader-v1"
        and state.get("complete") is True
        and state.get("status") == "COMPLETED"
        and source_matches
        and counts_match
        and valid_structure
        and summary["parts_total"] > 0
        and summary["parts_total"] == summary["parts_completed"]
        and summary["fragments_total"] > 0
        and summary["fragments_total"] == summary["fragments_covered"]
    )
    summary.update(complete=complete, status="COMPLETE" if complete else "INCOMPLETE")
    if not source_matches:
        summary.update(parts_completed=0, fragments_covered=0, status="STALE")
    return summary


def summarize_reading_audit(
    runs: list[dict[str, Any]],
    evidences: list[dict[str, Any]],
) -> dict[str, Any]:
    """Reconcile every archived item; never emit payloads, quotes or interpretations.

    Completion proves persisted, validated response coverage, not analytical
    correctness, sufficient market evidence, provider success or course viability.
    The caller must scope both collections to the authorized institution/analysis.
    """
    result: dict[str, Any] = {
        "schema_version": 1,
        "complete": False,
        "status": "UNVERIFIED",
        "runs_total": len(runs),
        "remote_runs_total": 0,
        "legacy_runs_without_archive": 0,
        "archives_total": 0,
        "archives_retrieval_complete": 0,
        "items_produced": 0,
        "items_produced_unknown_archives": 0,
        "items_retrieved": 0,
        "items_preserved": 0,
        "items_read": 0,
        "items_pending": 0,
        "parts_total": 0,
        "parts_completed": 0,
        "fragments_total": 0,
        "fragments_covered": 0,
        "normalized_evidences_total": len(evidences),
        "normalized_evidences_complete": 0,
        "normalized_evidences_pending": 0,
        "archives": [],
    }
    for run in runs:
        parameters = run.get("parameters")
        parameters = parameters if isinstance(parameters, dict) else {}
        previous = parameters.get("prior_dataset_archives")
        archives = (
            [archive for archive in previous if isinstance(archive, dict)]
            if isinstance(previous, list)
            else []
        )
        if isinstance(parameters.get("dataset_archive"), dict):
            archives.append(parameters["dataset_archive"])
        remote = bool(run.get("provider_run_id") or run.get("dataset_id"))
        result["remote_runs_total"] += int(remote)
        if remote and not any(
            archive.get("provider_run_id") == run.get("provider_run_id")
            and (not run.get("dataset_id") or archive.get("dataset_id") == run.get("dataset_id"))
            for archive in archives
        ):
            result["legacy_runs_without_archive"] += 1
        readings = parameters.get("dataset_readings")
        readings = readings if isinstance(readings, dict) else {}
        for archive in archives:
            produced = _count(archive.get("dataset_total_items"))
            retrieved = _count(archive.get("items_read"))
            items = archive.get("items")
            items = items if isinstance(items, list) else []
            issues = []
            indices = [item.get("index") for item in items if isinstance(item, dict)]
            indices_valid = (
                len(indices) == len(items)
                and all(_count(index) is not None for index in indices)
                and len(set(indices)) == len(indices)
                and sorted(index for index in indices if isinstance(index, int))
                == list(range(len(items)))
            )
            retrieval_complete = (
                archive.get("schema_version") == 1
                and all(
                    isinstance(archive.get(key), str) and archive[key]
                    for key in ("provider_run_id", "dataset_id", "source_sha256")
                )
                and archive.get("retrieval_complete") is True
                and archive.get("total_items_source")
                in {"provider_pagination", "terminal_exhaustion"}
                and produced is not None
                and produced == retrieved == len(items)
                and indices_valid
            )
            if not retrieval_complete:
                issues.append("retrieval_not_reconciled")
            row: dict[str, Any] = {
                "tool_run_id": str(run.get("id") or ""),
                "provider_run_id": str(archive.get("provider_run_id") or ""),
                "dataset_id": str(archive.get("dataset_id") or ""),
                "retrieval_complete": retrieval_complete,
                "complete": False,
                "items_produced": produced,
                "items_retrieved": retrieved,
                "items_preserved": len(items),
                "items_read": 0,
                "parts_total": 0,
                "parts_completed": 0,
                "fragments_total": 0,
                "fragments_covered": 0,
                "states": {},
                "issues": issues,
            }
            for position, item in enumerate(items):
                if not isinstance(item, dict) or not isinstance(item.get("sanitized_data"), dict):
                    issues.append("sanitized_item_missing")
                    row["states"]["MISSING"] = row["states"].get("MISSING", 0) + 1
                    continue
                expected_context = {
                    "tool_run_id": run.get("id"),
                    "provider_run_id": archive.get("provider_run_id"),
                    "dataset_id": archive.get("dataset_id"),
                    "archive_source_sha256": archive.get("source_sha256"),
                    "item_index": item.get("index"),
                    "item_position": position,
                    "item_source_sha256": item.get("source_sha256"),
                }
                candidates = [
                    state
                    for state in readings.values()
                    if isinstance(state, dict)
                    and isinstance(state.get("source_context"), dict)
                    and all(
                        state["source_context"].get(key) == value
                        for key, value in expected_context.items()
                    )
                ]
                summaries = [
                    _reading_summary(state, item["sanitized_data"]) for state in candidates
                ]
                summary = next(
                    (s for s in summaries if s["complete"]),
                    summaries[-1] if summaries else _reading_summary(None, {}),
                )
                row["items_read"] += int(summary["complete"])
                row["states"][summary["status"]] = row["states"].get(summary["status"], 0) + 1
                for field in (
                    "parts_total",
                    "parts_completed",
                    "fragments_total",
                    "fragments_covered",
                ):
                    row[field] += summary[field]
            row["items_pending"] = len(items) - row["items_read"]
            if row["items_pending"]:
                issues.append("item_reading_pending")
            row.update(
                complete=retrieval_complete and not row["items_pending"],
                status="COMPLETE"
                if retrieval_complete and not row["items_pending"]
                else "INCOMPLETE",
            )
            row["issues"] = list(dict.fromkeys(issues))
            result["archives"].append(row)
            result["archives_total"] += 1
            result["archives_retrieval_complete"] += int(retrieval_complete)
            result["items_produced"] += produced or 0
            result["items_produced_unknown_archives"] += int(produced is None)
            for field in (
                "items_retrieved",
                "items_preserved",
                "items_read",
                "items_pending",
                "parts_total",
                "parts_completed",
                "fragments_total",
                "fragments_covered",
            ):
                result[field] += row[field] or 0
    for evidence in evidences:
        payload = evidence.get("sanitized_data")
        if not isinstance(payload, dict):
            continue
        content = {
            key: value
            for key, value in payload.items()
            if key not in {"_reading", "_qualification"}
        }
        result["normalized_evidences_complete"] += int(
            _reading_summary(payload.get("_reading"), content)["complete"]
        )
    result["normalized_evidences_pending"] = (
        len(evidences) - result["normalized_evidences_complete"]
    )
    result["complete"] = (
        result["archives_total"] > 0
        and not result["legacy_runs_without_archive"]
        and all(row["complete"] for row in result["archives"])
        and not result["normalized_evidences_pending"]
    )
    result["status"] = (
        "COMPLETE"
        if result["complete"]
        else "INCOMPLETE"
        if result["archives_total"]
        else "UNVERIFIED"
    )
    return result
