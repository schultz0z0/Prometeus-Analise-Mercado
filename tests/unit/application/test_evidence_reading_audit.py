"""Manifesto público: cobertura verificável sem transportar conteúdo privado."""

import hashlib
import importlib
import importlib.util
import json
from copy import deepcopy

import pytest


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def state(payload, context=None):
    return {
        "version": "integral-reader-v1",
        "complete": True,
        "status": "COMPLETED",
        "manifest": {
            "source_hash": digest(payload),
            "total_parts": 1,
            "completed_parts": 1,
            "total_fragments": 1,
            "covered_fragments": 1,
        },
        "source_context": context or {},
        "parts": [
            {
                "part_id": "part",
                "fragments": [{"fragment_id": "fragment", "text": "PRIVATE"}],
                "result": {
                    "part_id": "part",
                    "observations": [
                        {"fragment_id": "fragment", "analysis": "PRIVATE", "quotes": ["PRIVATE"]},
                    ],
                },
            }
        ],
        "findings": [{"quote": "PRIVATE", "model_analysis": "PRIVATE"}],
    }


def run(run_id="remote", data=None):
    payload = {"text": "PRIVATE"} if data is None else data
    archive = {
        "schema_version": 1,
        "provider_run_id": run_id,
        "dataset_id": "dataset-" + run_id,
        "source_sha256": digest([payload]),
        "retrieval_complete": True,
        "dataset_total_items": 1,
        "items_read": 1,
        "total_items_source": "provider_pagination",
        "items": [
            {
                "index": 0,
                "source_sha256": digest(payload),
                "sanitized_data": payload,
                "raw_payload": {"secret": "RAW_PRIVATE"},
            }
        ],
    }
    context = {
        "tool_run_id": "tool",
        "provider_run_id": run_id,
        "dataset_id": "dataset-" + run_id,
        "archive_source_sha256": archive["source_sha256"],
        "item_index": 0,
        "item_position": 0,
        "item_source_sha256": digest(payload),
    }
    return {
        "id": "tool",
        "provider_run_id": run_id,
        "dataset_id": "dataset-" + run_id,
        "parameters": {
            "dataset_archive": archive,
            "dataset_readings": {"key": state(payload, context)},
        },
    }


def summarize(runs, evidences=()):
    module = "prometeus.application.evidence_reading_audit"
    assert importlib.util.find_spec(module) is not None, "Manifesto público ainda não implementado"
    return importlib.import_module(module).summarize_reading_audit(runs, list(evidences))


def test_complete_archive_and_normalized_evidence_are_counted_without_private_content():
    source = run()
    payload = {"normalized": "PRIVATE"}
    evidence = {
        "id": "evidence",
        "sanitized_data": {
            **payload,
            "_reading": state(payload),
            "_qualification": {"reason": "PRIVATE"},
        },
    }
    original = deepcopy((source, evidence))
    result = summarize([source], [evidence])
    assert result["complete"] and result["status"] == "COMPLETE"
    assert (
        result["items_produced"],
        result["items_retrieved"],
        result["items_preserved"],
        result["items_read"],
    ) == (1, 1, 1, 1)
    assert (result["fragments_total"], result["fragments_covered"]) == (1, 1)
    assert result["normalized_evidences_complete"] == 1
    assert "PRIVATE" not in json.dumps(result)
    assert not {"raw_payload", "sanitized_data", "parts", "findings", "model_analysis"} & set(
        result
    )
    assert (source, evidence) == original


def test_prior_archives_and_duplicate_records_are_counted_individually():
    current, old = run(), run("prior")
    current["parameters"]["prior_dataset_archives"] = [old["parameters"]["dataset_archive"]]
    current["parameters"]["dataset_readings"]["old-key"] = old["parameters"]["dataset_readings"][
        "key"
    ]
    result = summarize([current])
    assert result["complete"]
    assert result["archives_total"] == 2 and result["items_read"] == 2
    assert {row["provider_run_id"] for row in result["archives"]} == {"prior", "remote"}


def test_prior_complete_archive_does_not_hide_missing_output_of_current_remote_run():
    current, old = run(), run("prior")
    del current["parameters"]["dataset_archive"]
    current["parameters"]["prior_dataset_archives"] = [old["parameters"]["dataset_archive"]]
    current["parameters"]["dataset_readings"] = old["parameters"]["dataset_readings"]
    result = summarize([current])
    assert not result["complete"]
    assert result["legacy_runs_without_archive"] == 1


@pytest.mark.parametrize(
    "mutation",
    [
        "retrieval",
        "count",
        "source",
        "parts",
        "fragments",
        "context",
        "hash",
        "status",
        "archive_version",
    ],
)
def test_inconsistent_or_incomplete_manifests_never_claim_complete(mutation):
    source = run()
    archive = source["parameters"]["dataset_archive"]
    reading = source["parameters"]["dataset_readings"]["key"]
    if mutation == "retrieval":
        archive["retrieval_complete"] = False
    elif mutation == "count":
        archive["dataset_total_items"] = 2
    elif mutation == "source":
        archive["total_items_source"] = "unverified"
    elif mutation == "parts":
        reading["parts"][0]["result"] = None
    elif mutation == "fragments":
        reading["manifest"]["covered_fragments"] = 0
    elif mutation == "context":
        reading["source_context"]["provider_run_id"] = "other"
    elif mutation == "hash":
        reading["manifest"]["source_hash"] = "stale"
    elif mutation == "archive_version":
        archive["schema_version"] = 999
    else:
        reading["status"] = "INCOMPLETE"
    assert not summarize([source])["complete"]


def test_remote_legacy_without_archive_and_empty_analysis_remain_unverified():
    result = summarize([{"id": "legacy", "provider_run_id": "remote", "parameters": {}}])
    assert not result["complete"] and result["status"] == "UNVERIFIED"
    assert result["legacy_runs_without_archive"] == 1
    assert not summarize([])["complete"]


def test_empty_verified_dataset_complete_but_unread_normalized_evidence_blocks_completion():
    source = run()
    source["parameters"]["dataset_archive"].update(items=[], items_read=0, dataset_total_items=0)
    source["parameters"]["dataset_readings"] = {}
    assert summarize([source])["complete"]
    result = summarize([source], [{"id": "legacy-evidence", "sanitized_data": {"text": "unread"}}])
    assert not result["complete"] and result["normalized_evidences_complete"] == 0
