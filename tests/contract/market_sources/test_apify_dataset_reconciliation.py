"""Reconciliation preserves paid output and records the failing page, without POST."""

import httpx
import pytest

from prometeus.domain.configuration import AppSettings
from prometeus.domain.research import PlannedToolCall
from prometeus.infrastructure.apify.client import (
    ApifyClient,
    ApifyReconciliationRequiredError,
    ApifySchemaDriftError,
)
from prometeus.infrastructure.apify.registry import ApifyActorRegistry


def make_client(handler):
    registry = ApifyActorRegistry.from_settings(AppSettings(
        _env_file=None, APIFY_ACTOR_GOOGLE_SEARCH="apify/google-search-scraper@0.0.474",
    ))
    return ApifyClient(api_token="private-test-token", registry=registry,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))


CALL = PlannedToolCall(capability="google_search", query="curso seguros", rationale="reconcile")
RUN = {"id": "existing-run", "status": "SUCCEEDED", "defaultDatasetId": "paid-dataset",
       "buildNumber": "0.0.474", "usageTotalUsd": 0.02}


@pytest.mark.asyncio
@pytest.mark.parametrize("reported,rows", [
    (2, [{"title": "Existing paid row", "#debug": {"kept": True}}]),
    (1, []),
    (0, [{"title": "Existing paid row"}]),
])
async def test_count_mismatch_retains_response_and_structured_diagnostic(reported, rows):
    requests = []

    def handler(request):
        requests.append(request)
        if "/datasets/" in request.url.path:
            return httpx.Response(200, json=rows, headers={
                "X-Apify-Pagination-Total": str(reported),
                "X-Apify-Pagination-Count": str(len(rows)),
            })
        return httpx.Response(200, json={"data": RUN})

    client = make_client(handler)
    try:
        with pytest.raises(ApifyReconciliationRequiredError) as caught:
            await client.resume(CALL, run_id="existing-run")
        error = caught.value
        assert error.dataset_result is not None
        assert error.dataset_result.items == rows
        assert error.dataset_result.total_items == reported
        assert error.dataset_result.total_items_source == "unverified"
        diagnostic = error.pagination_diagnostic
        assert diagnostic["requested_offset"] == 0
        assert diagnostic["requested_limit"] == 1000
        assert diagnostic["returned_items"] == len(rows)
        assert diagnostic["reported_total"] == reported
        assert diagnostic["reason"] == "page_count_mismatch"
        assert "private-test-token" not in str(diagnostic)
        assert all(request.method == "GET" for request in requests)
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_failed_second_page_keeps_prefix_and_records_request_without_secrets():
    prefix = [{"title": f"Row {i}"} for i in range(1000)]

    def handler(request):
        if "/datasets/" in request.url.path:
            if request.url.params["offset"] == "0":
                return httpx.Response(200, json=prefix,
                    headers={"X-Apify-Pagination-Total": "1001"})
            return httpx.Response(503)
        return httpx.Response(200, json={"data": RUN})

    client = make_client(handler)
    try:
        with pytest.raises(ApifyReconciliationRequiredError) as caught:
            await client.resume(CALL, run_id="existing-run")
        assert caught.value.dataset_result is not None
        assert caught.value.dataset_result.items == prefix
        assert caught.value.pagination_diagnostic["requested_offset"] == 1000
        assert caught.value.pagination_diagnostic["http_status"] == 503
        assert caught.value.pagination_diagnostic["reason"] == "dataset_http_error"
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_changed_total_preserves_both_pages_as_unverified_output():
    prefix = [{"title": f"Row {i}"} for i in range(1000)]
    tail = [{"title": "Tail while count changed"}]

    def handler(request):
        if "/datasets/" in request.url.path:
            first = request.url.params["offset"] == "0"
            return httpx.Response(200, json=prefix if first else tail,
                headers={"X-Apify-Pagination-Total": "1001" if first else "1002"})
        return httpx.Response(200, json={"data": RUN})

    client = make_client(handler)
    try:
        with pytest.raises(ApifyReconciliationRequiredError) as caught:
            await client.resume(CALL, run_id="existing-run")
        assert caught.value.dataset_result is not None
        assert caught.value.dataset_result.items == prefix + tail
        assert caught.value.dataset_result.total_items_source == "unverified"
        assert caught.value.pagination_diagnostic["previous_reported_total"] == 1001
        assert caught.value.pagination_diagnostic["reported_total"] == 1002
        assert caught.value.pagination_diagnostic["reason"] == "dataset_total_changed"
    finally:
        await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_page", ["not-json", '{"unexpected":"object"}'])
async def test_invalid_later_page_preserves_valid_prefix_without_admitting_bad_schema(invalid_page):
    prefix = [{"title": f"Row {i}"} for i in range(1000)]

    def handler(request):
        if "/datasets/" in request.url.path:
            if request.url.params["offset"] == "0":
                return httpx.Response(200, json=prefix,
                    headers={"X-Apify-Pagination-Total": "1001"})
            return httpx.Response(200, text=invalid_page)
        return httpx.Response(200, json={"data": RUN})

    client = make_client(handler)
    try:
        with pytest.raises(ApifySchemaDriftError) as caught:
            await client.resume(CALL, run_id="existing-run")
        assert caught.value.dataset_result is not None
        assert caught.value.dataset_result.items == prefix
        assert caught.value.dataset_result.total_items_source == "unverified"
        assert caught.value.pagination_diagnostic["requested_offset"] == 1000
        assert caught.value.pagination_diagnostic["reason"] == "dataset_schema_error"
    finally:
        await client.aclose()
