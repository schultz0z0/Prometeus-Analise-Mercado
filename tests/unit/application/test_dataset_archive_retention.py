"""A shorter failed reread must never erase already downloaded paid records."""

from copy import deepcopy

from prometeus.application.collect_market_evidence import CollectMarketEvidenceService
from prometeus.infrastructure.apify.schemas import ApifyExecutionResult, ApifyRunMetadata


def result(items, *, total=None, verified=True, run="run", dataset="dataset"):
    return ApifyExecutionResult(
        run=ApifyRunMetadata(run_id=run, dataset_id=dataset, status="FAILED",
                             actor_id="actor/test", build_number="1.0.0"),
        items=items, total_items=len(items) if total is None else total,
        total_items_source="provider_pagination" if verified else "unverified",
    )


def service():
    return CollectMarketEvidenceService(None, None, None)


def test_empty_failed_reread_keeps_the_larger_prefix_and_attempt_diagnostics():
    collector = service()
    rows = [{"unknown": {"tail": i}} for i in range(1000)]
    original = {"dataset_archive": collector._dataset_archive(result(rows, total=1001)),
                "dataset_read_pending": True, "unrelated": "keep"}
    before = deepcopy(original)
    retained = collector._retain_dataset_archive(original, result([], verified=False))
    archive = retained["dataset_archive"]
    assert archive["items_read"] == 1000 and archive["dataset_total_items"] == 1001
    assert archive["items"][-1]["raw_payload"] == rows[-1]
    assert archive["retrieval_complete"] is False
    assert not retained.get("prior_dataset_archives")
    assert archive["retrieval_snapshots"][-1]["items_read"] == 0
    assert retained["unrelated"] == "keep" and original == before


def test_compatible_complete_reread_subsumes_prefix_and_clears_pending_without_old_partial_gate():
    collector = service()
    rows = [{"unknown": i} for i in range(5)]
    parameters = {"dataset_archive": collector._dataset_archive(result(rows[:3], total=5)),
                  "dataset_read_pending": True, "dataset_read_recovery": "resume_existing_provider_run"}
    parameters = collector._retain_dataset_archive(parameters, result(rows[:2], total=5))
    assert parameters["dataset_archive"]["items_read"] == 3
    parameters = collector._retain_dataset_archive(parameters, result(rows))
    assert parameters["dataset_archive"]["retrieval_complete"] is True
    assert parameters["dataset_archive"]["items_read"] == 5
    assert parameters["dataset_read_pending"] is False
    assert not parameters.get("prior_dataset_archives")


def test_same_index_divergence_preserves_both_versions_and_requires_integrity_review():
    collector = service()
    original = collector._dataset_archive(result([{"value": "first"}]))
    parameters = collector._retain_dataset_archive({"dataset_archive": original}, result([{"value": "second"}]))
    assert parameters["prior_dataset_archives"] == [original]
    assert parameters["dataset_archive"]["items"][0]["raw_payload"]["value"] == "second"
    assert parameters["dataset_archive"]["retrieval_complete"] is False
    assert parameters["dataset_integrity_review_required"] is True
    # Repeating the second version cannot erase the already observed conflict.
    parameters = collector._retain_dataset_archive(parameters, result([{"value": "second"}]))
    assert parameters["dataset_archive"]["retrieval_complete"] is False
    assert len(parameters["prior_dataset_archives"]) == 1


def test_complete_shorter_dataset_is_mutation_even_when_it_matches_a_prefix():
    collector = service()
    original = collector._dataset_archive(result([{"value": 1}, {"value": 2}]))
    retained = collector._retain_dataset_archive({"dataset_archive": original}, result([{"value": 1}]))
    assert retained["dataset_integrity_review_required"] is True
    assert retained["prior_dataset_archives"] == [original]
    assert retained["dataset_archive"]["retrieval_complete"] is False


def test_distinct_provider_run_keeps_previous_snapshot_and_no_false_conflict():
    collector = service()
    original = collector._dataset_archive(result([{"value": 1}]))
    retained = collector._retain_dataset_archive({"dataset_archive": original}, result([{"value": 2}], run="next"))
    assert retained["prior_dataset_archives"] == [original]
    assert retained["dataset_archive"]["retrieval_complete"] is True
    assert not retained.get("dataset_integrity_review_required")
