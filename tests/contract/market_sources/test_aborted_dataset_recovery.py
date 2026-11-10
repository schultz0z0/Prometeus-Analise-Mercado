"""Recover paid output before retrying an Actor; no external requests."""

import httpx
import pytest

from prometeus.application.recover_market_collection import diagnose
from prometeus.domain.configuration import AppSettings
from prometeus.domain.research import PlannedToolCall
from prometeus.infrastructure.apify.client import (
    ApifyActorFailedError,
    ApifyClient,
    ApifyReconciliationRequiredError,
    ApifyTimeoutError,
)
from prometeus.infrastructure.apify.registry import ApifyActorRegistry


def setup(handler):
    registry = ApifyActorRegistry.from_settings(AppSettings(
        _env_file=None, APIFY_ACTOR_GOOGLE_TRENDS="apify/google-trends-scraper@0.0.143",
    ))
    return ApifyClient(
        api_token="test", registry=registry,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    ), PlannedToolCall(capability="google_trends", query="curso", rationale="review")


@pytest.mark.asyncio
async def test_aborted_dataset_page_failure_preserves_read_prefix_and_requires_same_run_get():
    requests = []
    data = {"id": "run", "status": "ABORTED", "defaultDatasetId": "dataset",
            "buildNumber": "0.0.143", "usageTotalUsd": 0.15}

    def handler(request):
        requests.append(request)
        if "/datasets/" in request.url.path:
            if request.url.params.get("offset") == "0":
                return httpx.Response(200, json=[{"keyword": "curso", "unknown": i} for i in range(1000)],
                                      headers={"X-Apify-Pagination-Total": "1001"})
            return httpx.Response(500)
        return httpx.Response(200, json={"data": data})

    client, call = setup(handler)
    try:
        with pytest.raises(ApifyTimeoutError) as caught:
            await client.resume(call, run_id="run")
        error = caught.value
        assert error.dataset_read_pending is True
        assert len(error.dataset_result.items) == 1000
        assert error.dataset_result.total_items == 1001
        assert error.dataset_result.total_items_source == "unverified"
        assert error.dataset_result.run.run_id == "run"
        assert diagnose(error, 1).action == "reconcile_existing_run"
        assert all(request.method == "GET" for request in requests)
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_aborted_verified_empty_dataset_retains_its_retrieval_manifest():
    data = {"id": "run", "status": "ABORTED", "defaultDatasetId": "dataset",
            "buildNumber": "0.0.143", "usageTotalUsd": 0.15}

    def handler(request):
        if "/datasets/" in request.url.path:
            return httpx.Response(200, json=[], headers={"X-Apify-Pagination-Total": "0"})
        return httpx.Response(200, json={"data": data})

    client, call = setup(handler)
    try:
        with pytest.raises(ApifyTimeoutError) as caught:
            await client.resume(call, run_id="run")
        assert caught.value.dataset_result.items == []
        assert caught.value.dataset_result.total_items_source == "provider_pagination"
        assert caught.value.dataset_result.total_items == 0
        assert caught.value.dataset_read_pending is False
    finally:
        await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["FAILED", "TIMED-OUT"])
async def test_failed_terminal_build_id_resolves_before_archiving_output(status):
    requests = []
    data = {"id": "run", "status": status, "defaultDatasetId": "dataset",
            "buildId": "build", "actId": "actor", "usageTotalUsd": 0.15}

    def handler(request):
        requests.append(request)
        if "/actor-builds/" in request.url.path:
            return httpx.Response(200, json={"data": {
                "id": "build", "actId": "actor", "buildNumber": "0.0.143",
            }})
        if "/datasets/" in request.url.path:
            return httpx.Response(200, json=[{"keyword": "curso", "unknown": {"kept": True}}],
                                  headers={"X-Apify-Pagination-Total": "1"})
        return httpx.Response(200, json={"data": data})

    client, call = setup(handler)
    try:
        with pytest.raises(ApifyActorFailedError) as caught:
            await client.resume(call, run_id="run")
        error = caught.value
        assert error.dataset_result.run.build_number == "0.0.143"
        assert error.dataset_result.run.status == status
        assert error.dataset_result.items == [{"keyword": "curso", "unknown": {"kept": True}}]
        assert error.dataset_read_pending is False
        assert all(request.method == "GET" for request in requests)
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_failed_build_resolution_still_rejects_actor_identity_mismatch():
    paths = []
    data = {"id": "run", "status": "FAILED", "defaultDatasetId": "dataset",
            "buildId": "build", "actId": "actor", "usageTotalUsd": 0.15}

    def handler(request):
        paths.append(request.url.path)
        if "/actor-builds/" in request.url.path:
            return httpx.Response(200, json={"data": {
                "id": "build", "actId": "different-actor", "buildNumber": "0.0.143",
            }})
        return httpx.Response(200, json={"data": data})

    client, call = setup(handler)
    try:
        with pytest.raises(ApifyReconciliationRequiredError):
            await client.resume(call, run_id="run")
        assert not any("/datasets/" in path for path in paths)
    finally:
        await client.aclose()
