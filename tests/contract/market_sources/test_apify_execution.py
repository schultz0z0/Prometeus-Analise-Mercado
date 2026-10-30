from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from prometeus.domain.configuration import AppSettings
from prometeus.domain.research import PlannedToolCall
from prometeus.infrastructure.apify.client import (
    ApifyActorFailedError,
    ApifyClient,
    ApifySchemaDriftError,
    ApifyTimeoutError,
)
from prometeus.infrastructure.apify.registry import ApifyActorRegistry


def make_client(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    max_poll_attempts: int = 3,
) -> ApifyClient:
    settings = AppSettings(
        _env_file=None,
        APIFY_TOKEN="apify-token-for-test",
        APIFY_ACTOR_GOOGLE_SEARCH="apify/google-search-scraper@0.0.473",
    )
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return ApifyClient(
        api_token=settings.APIFY_TOKEN,
        registry=ApifyActorRegistry.from_settings(settings),
        http_client=http_client,
        polling_interval_seconds=0,
        max_poll_attempts=max_poll_attempts,
    )


def google_call() -> PlannedToolCall:
    return PlannedToolCall(
        id="google-call",
        capability="google_search",
        query="curso gestão de seguros",
        rationale="mapear oferta",
        max_items=20,
        parameters={"country": "BR", "language": "pt"},
    )


@pytest.mark.asyncio
async def test_execute_uses_official_urls_pinned_build_budget_and_run_metadata() -> None:
    requests: list[httpx.Request] = []
    poll_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal poll_count
        requests.append(request)
        if request.method == "POST":
            return httpx.Response(
                201,
                json={
                    "data": {
                        "id": "run-123",
                        "status": "RUNNING",
                        "defaultDatasetId": "dataset-123",
                        "buildNumber": "0.0.473",
                    }
                },
            )
        if request.url.path.endswith("/actor-runs/run-123"):
            poll_count += 1
            return httpx.Response(
                200,
                json={
                    "data": {
                        "id": "run-123",
                        "status": "SUCCEEDED",
                        "defaultDatasetId": "dataset-123",
                        "buildNumber": "0.0.473",
                        "usageTotalUsd": 0.0173,
                    }
                },
            )
        return httpx.Response(
            200,
            headers={"X-Apify-Pagination-Total": "1"},
            json=[
                {
                    "title": "MBA em Gestão de Seguros",
                    "url": "https://example.edu/mba-seguros",
                    "description": "Oferta encontrada no resultado orgânico.",
                }
            ],
        )

    client = make_client(handler)
    try:
        result = await client.execute(google_call(), max_total_charge_usd=0.25)
    finally:
        await client.aclose()

    start = requests[0]
    assert start.url.path == "/v2/actors/apify~google-search-scraper/runs"
    assert start.url.params["build"] == "0.0.473"
    assert start.url.params["maxItems"] == "20"
    assert start.url.params["maxTotalChargeUsd"] == "0.25"
    assert start.headers["authorization"] == "Bearer apify-token-for-test"
    assert poll_count == 1
    assert result.run.run_id == "run-123"
    assert result.run.dataset_id == "dataset-123"
    assert result.run.cost_usd == 0.0173
    assert result.run.build_number == "0.0.473"
    assert result.total_items == 1
    assert result.items[0]["url"] == "https://example.edu/mba-seguros"


@pytest.mark.asyncio
async def test_execute_preserves_successful_empty_dataset_as_observed_empty_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                201,
                json={
                    "data": {
                        "id": "run-empty",
                        "status": "SUCCEEDED",
                        "defaultDatasetId": "dataset-empty",
                        "buildNumber": "0.0.473",
                        "usageTotalUsd": 0.01,
                    }
                },
            )
        return httpx.Response(
            200,
            headers={"X-Apify-Pagination-Total": "0"},
            json=[],
        )

    client = make_client(handler)
    try:
        result = await client.execute(google_call(), max_total_charge_usd=0.25)
    finally:
        await client.aclose()

    assert result.items == []
    assert result.total_items == 0
    assert result.run.status == "SUCCEEDED"


@pytest.mark.asyncio
async def test_execute_raises_structured_error_for_terminal_actor_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            201,
            json={
                "data": {
                    "id": "run-failed",
                    "status": "FAILED",
                    "statusMessage": "Actor failed without exposing credentials",
                    "defaultDatasetId": "dataset-failed",
                    "buildNumber": "0.0.473",
                }
            },
        )

    client = make_client(handler)
    try:
        with pytest.raises(ApifyActorFailedError) as exc_info:
            await client.execute(google_call(), max_total_charge_usd=0.25)
    finally:
        await client.aclose()

    assert exc_info.value.run_id == "run-failed"
    assert exc_info.value.status == "FAILED"


@pytest.mark.asyncio
@pytest.mark.parametrize("abort_status", [200, 503])
async def test_execute_times_out_if_actor_never_reaches_terminal_state(abort_status: int) -> None:
    aborted = []

    def handler(request: httpx.Request) -> httpx.Response:
        status = "RUNNING"
        if request.url.path.endswith("/abort"):
            aborted.append(request.url.path)
            status = "ABORTED"
            if abort_status == 503:
                return httpx.Response(503, json={"error": "provider unavailable"})
        return httpx.Response(
            201 if request.method == "POST" else 200,
            json={
                "data": {
                    "id": "run-slow",
                    "status": status,
                    "defaultDatasetId": "dataset-slow",
                    "buildNumber": "0.0.473",
                }
            },
        )

    client = make_client(handler, max_poll_attempts=2)
    try:
        with pytest.raises(ApifyTimeoutError, match="run-slow") as exc_info:
            await client.execute(google_call(), max_total_charge_usd=0.25)
    finally:
        await client.aclose()
    assert aborted == ["/v2/actor-runs/run-slow/abort"]
    assert exc_info.value.run_id == "run-slow"
    assert ("não confirmado" in str(exc_info.value)) is (abort_status == 503)


@pytest.mark.asyncio
async def test_execute_rejects_dataset_schema_drift() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                201,
                json={
                    "data": {
                        "id": "run-drift",
                        "status": "SUCCEEDED",
                        "defaultDatasetId": "dataset-drift",
                        "buildNumber": "0.0.473",
                    }
                },
            )
        return httpx.Response(200, json=[{"unexpected": {"nested": "value"}}])

    client = make_client(handler)
    try:
        with pytest.raises(ApifySchemaDriftError, match="google_search"):
            await client.execute(google_call(), max_total_charge_usd=0.25)
    finally:
        await client.aclose()
