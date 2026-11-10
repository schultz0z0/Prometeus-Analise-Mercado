import httpx
import pytest

from prometeus.domain.configuration import AppSettings
from prometeus.domain.research import PlannedToolCall
from prometeus.infrastructure.apify.client import (
    ApifyActorFailedError,
    ApifyClient,
    ApifyReconciliationRequiredError,
    ApifySchemaDriftError,
)
from prometeus.infrastructure.apify.registry import ApifyActorRegistry


def client_for(handler):
    settings = AppSettings(
        _env_file=None, APIFY_ACTOR_GOOGLE_SEARCH="apify/google-search-scraper@0.0.473"
    )
    return ApifyClient(
        api_token="test-token",
        registry=ApifyActorRegistry.from_settings(settings),
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        polling_interval_seconds=0,
    )


def call():
    return PlannedToolCall(capability="google_search", query="curso", rationale="test", max_items=1)


def terminal():
    return httpx.Response(
        201,
        json={
            "data": {
                "id": "run",
                "status": "SUCCEEDED",
                "defaultDatasetId": "dataset",
                "buildNumber": "0.0.473",
            }
        },
    )


@pytest.mark.asyncio
async def test_reads_entire_produced_dataset_and_keeps_hidden_fields_beyond_planned_scope():
    rows = [
        {"title": f"Curso {i}", "url": f"https://school.test/{i}", "#debug": {"retained": i}}
        for i in range(1003)
    ]
    reads = []

    def handler(request):
        if request.method == "POST":
            return terminal()
        offset = int(request.url.params.get("offset", 0))
        limit = int(request.url.params.get("limit", 0))
        reads.append((offset, limit, request.url.params.get("clean")))
        return httpx.Response(
            200,
            headers={"X-Apify-Pagination-Total": str(len(rows))},
            json=rows[offset : offset + limit],
        )

    client = client_for(handler)
    try:
        result = await client.execute(call(), max_total_charge_usd=None)
    finally:
        await client.aclose()
    assert result.items == rows
    assert result.total_items == 1003
    assert [r[0] for r in reads] == [0, 1000]
    assert all(r[2] == "false" for r in reads)


@pytest.mark.asyncio
@pytest.mark.parametrize("second_total,second_rows", [(1004, [{"title": "tail"}] * 3), (1003, [])])
async def test_does_not_report_complete_when_provider_count_changes_or_a_page_disappears(
    second_total, second_rows
):
    def handler(request):
        if request.method == "POST":
            return terminal()
        offset = int(request.url.params.get("offset", 0))
        if not offset:
            return httpx.Response(
                200,
                headers={"X-Apify-Pagination-Total": "1003"},
                json=[{"title": str(i)} for i in range(1000)],
            )
        return httpx.Response(
            200, headers={"X-Apify-Pagination-Total": str(second_total)}, json=second_rows
        )

    client = client_for(handler)
    try:
        with pytest.raises(ApifyReconciliationRequiredError):
            await client.execute(call(), max_total_charge_usd=None)
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_exhausts_full_pages_without_fabricating_a_provider_reported_count():
    reads = []

    def handler(request):
        if request.method == "POST":
            return terminal()
        offset = int(request.url.params.get("offset", 0))
        reads.append(offset)
        return httpx.Response(
            200, json=[{"title": str(i)} for i in range(1000)] if not offset else []
        )

    client = client_for(handler)
    try:
        result = await client.execute(call(), max_total_charge_usd=None)
    finally:
        await client.aclose()
    assert len(result.items) == 1000
    assert reads == [0, 1000]
    assert result.total_items_source == "terminal_exhaustion"


@pytest.mark.asyncio
async def test_eventually_consistent_empty_page_requires_reconciliation_of_the_same_paid_run():
    starts = []
    reads = []

    def handler(request):
        if request.method == "POST":
            starts.append(request.url.path)
            return terminal()
        if "/actor-runs/" in request.url.path:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "id": "run",
                        "status": "SUCCEEDED",
                        "defaultDatasetId": "dataset",
                        "buildNumber": "0.0.473",
                    }
                },
            )
        reads.append(request.url.path)
        return httpx.Response(
            200,
            headers={"X-Apify-Pagination-Total": "1"},
            json=[] if len(reads) == 1 else [{"title": "Late item"}],
        )

    client = client_for(handler)
    try:
        with pytest.raises(ApifyReconciliationRequiredError):
            await client.execute(call(), max_total_charge_usd=None)
        result = await client.resume(call(), run_id="run")
    finally:
        await client.aclose()
    assert len(starts) == 1
    assert result.items == [{"title": "Late item"}]
    assert result.total_items == 1


@pytest.mark.asyncio
async def test_schema_drift_retains_the_entire_dataset_for_private_audit():
    rows = [{"new_unknown_shape": i} for i in range(1001)]
    reads = []

    def handler(request):
        if request.method == "POST":
            return terminal()
        offset = int(request.url.params.get("offset", 0))
        reads.append(offset)
        return httpx.Response(
            200, headers={"X-Apify-Pagination-Total": "1001"}, json=rows[offset : offset + 1000]
        )

    client = client_for(handler)
    try:
        with pytest.raises(ApifySchemaDriftError) as caught:
            await client.execute(call(), max_total_charge_usd=None)
    finally:
        await client.aclose()
    assert reads == [0, 1000]
    assert caught.value.dataset_result.items == rows
    assert caught.value.dataset_result.total_items_source == "provider_pagination"


@pytest.mark.asyncio
async def test_failed_actor_dataset_error_preserves_original_failure_and_recoverable_checkpoint():
    def handler(request):
        if request.method == "POST":
            return httpx.Response(
                201,
                json={
                    "data": {
                        "id": "run",
                        "status": "FAILED",
                        "defaultDatasetId": "dataset",
                        "buildNumber": "0.0.473",
                    }
                },
            )
        offset = int(request.url.params.get("offset", 0))
        if offset:
            return httpx.Response(503, json={"error": "temporary"})
        return httpx.Response(
            200,
            headers={"X-Apify-Pagination-Total": "1001"},
            json=[{"title": str(i)} for i in range(1000)],
        )

    client = client_for(handler)
    try:
        with pytest.raises(ApifyActorFailedError) as caught:
            await client.execute(call(), max_total_charge_usd=None)
    finally:
        await client.aclose()
    assert caught.value.status == "FAILED"
    assert caught.value.dataset_read_pending is True
    assert caught.value.dataset_result.total_items == 1001
    assert len(caught.value.dataset_result.items) == 1000
    assert caught.value.dataset_result.total_items_source == "unverified"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["FAILED", "TIMED-OUT"])
async def test_failed_actor_retains_produced_rows_without_changing_its_failed_outcome(status):
    rows = [{"title": "Produced before failure", "#diagnostics": {"status": status}}]

    def handler(request):
        if request.method == "POST":
            return httpx.Response(
                201,
                json={
                    "data": {
                        "id": "run",
                        "status": status,
                        "defaultDatasetId": "dataset",
                        "buildNumber": "0.0.473",
                    }
                },
            )
        return httpx.Response(200, headers={"X-Apify-Pagination-Total": "1"}, json=rows)

    client = client_for(handler)
    try:
        with pytest.raises(ApifyActorFailedError) as caught:
            await client.execute(call(), max_total_charge_usd=None)
    finally:
        await client.aclose()
    assert caught.value.status == status
    assert caught.value.dataset_result.items == rows
