from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from prometeus.domain.configuration import AppSettings
from prometeus.domain.research import PlannedToolCall
from prometeus.infrastructure.apify.client import (
    ApifyActorFailedError,
    ApifyClient,
    ApifyReconciliationRequiredError,
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
async def test_monitoring_execute_omits_money_cap_and_checkpoints_run_before_polling():
    seen = []
    checkpointed = []

    def handler(request):
        seen.append(request)
        if request.method == "POST":
            assert "maxTotalChargeUsd" not in request.url.params
            assert "maxItems" not in request.url.params
            assert json.loads(request.content)["maxPagesPerQuery"] >= 1
            return httpx.Response(201, json={"data": {
                "id": "run-monitor", "status": "RUNNING", "defaultDatasetId": "dataset",
                "buildNumber": "0.0.473",
            }})
        assert checkpointed == ["run-monitor"]
        if "/actor-runs/" in request.url.path:
            return httpx.Response(200, json={"data": {
                "id": "run-monitor", "status": "SUCCEEDED", "defaultDatasetId": "dataset",
                "buildNumber": "0.0.473", "usageTotalUsd": 0.1,
            }})
        return httpx.Response(200, json=[])

    async def started(data):
        checkpointed.append(data["id"])

    result = await make_client(handler).execute(
        google_call(), max_total_charge_usd=None, on_run_started=started,
    )
    assert result.run.run_id == "run-monitor"
    assert sum(r.method == "POST" for r in seen) == 1


@pytest.mark.asyncio
async def test_monitoring_resume_retries_dataset_get_without_another_actor():
    dataset_calls = 0

    def handler(request):
        nonlocal dataset_calls
        assert request.method == "GET"
        if "/actor-runs/" in request.url.path:
            return httpx.Response(200, json={"data": {
                "id": "prior-run", "status": "SUCCEEDED", "defaultDatasetId": "dataset",
                "buildNumber": "0.0.473", "usageTotalUsd": 0.02,
            }})
        dataset_calls += 1
        if dataset_calls == 1:
            return httpx.Response(502)
        return httpx.Response(200, json=[])

    client = make_client(handler)
    with pytest.raises(ApifyReconciliationRequiredError):
        await client.resume(google_call(), run_id="prior-run")
    result = await client.resume(google_call(), run_id="prior-run")
    assert result.run.run_id == "prior-run"
    assert dataset_calls == 2


@pytest.mark.asyncio
async def test_find_uncertain_start_matches_actor_input_and_time_without_post():
    from datetime import UTC, datetime

    def handler(request):
        assert request.method == "GET"
        if request.url.path.endswith("/runs"):
            return httpx.Response(200, json={"data": {"items": [
                {"id": "candidate", "buildNumber": "0.0.473", "startedAt": "2026-11-05T12:00:02Z", "defaultKeyValueStoreId": "store"},
                {"id": "old", "buildNumber": "0.0.473", "startedAt": "2026-11-04T12:00:02Z", "defaultKeyValueStoreId": "oldstore"},
            ]}})
        assert "/store/records/INPUT" in request.url.path
        return httpx.Response(200, json={"queries": "expected"})

    result = await make_client(handler).find_started_run(
        google_call(), started_at=datetime(2026, 11, 5, 12, tzinfo=UTC),
        actor_input={"queries": "expected"},
    )
    assert result["id"] == "candidate"


@pytest.mark.asyncio
async def test_cancel_during_resume_aborts_known_run_before_exiting():
    import asyncio

    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"data": {"id": "known", "status": "ABORTED"}})

    async def cancelled():
        return False

    client = make_client(handler)
    client.cancellation_check = cancelled
    with pytest.raises(asyncio.CancelledError):
        await client.resume(google_call(), run_id="known")
    assert [(r.method, r.url.path) for r in requests] == [("POST", "/v2/actor-runs/known/abort")]


@pytest.mark.asyncio
async def test_provider_rejection_preserves_reason_without_exposing_token():
    def handler(request):
        return httpx.Response(400, json={"error": {"type": "max-total-charge-usd-below-minimum", "message": "minimum 0.50; apify-token-for-test"}})

    with pytest.raises(httpx.HTTPStatusError) as captured:
        await make_client(handler).execute(google_call(), max_total_charge_usd=None)
    assert getattr(captured.value, "provider_error_code", None) == "max-total-charge-usd-below-minimum"
    assert "minimum 0.50" in str(captured.value)
    assert "apify-token-for-test" not in str(captured.value)


@pytest.mark.asyncio
async def test_resume_confirmed_aborted_run_recovers_persisted_partial_items():
    def handler(request):
        assert request.method == "GET"
        if "/actor-runs/" in request.url.path:
            return httpx.Response(200, json={"data": {"id": "aborted-run", "status": "ABORTED", "defaultDatasetId": "partial-dataset", "buildNumber": "0.0.473", "usageTotalUsd": 0.03}})
        return httpx.Response(200, json=[{"title": "Curso IA", "url": "https://fgv.br/curso/ia"}])

    result = await make_client(handler).resume(google_call(), run_id="aborted-run")
    assert result.run.status == "ABORTED"
    assert result.run.incomplete_reason is not None
    assert len(result.items) == 1


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
                    "usageTotalUsd": 0.0,
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
                    "usageTotalUsd": 0.0,
                    "defaultDatasetId": "dataset-slow",
                    "buildNumber": "0.0.473",
                }
            },
        )

    client = make_client(handler, max_poll_attempts=2)
    try:
        expected_error = (
            ApifyTimeoutError if abort_status == 200 else ApifyReconciliationRequiredError
        )
        with pytest.raises(expected_error, match="run-slow") as exc_info:
            await client.execute(google_call(), max_total_charge_usd=0.25)
    finally:
        await client.aclose()
    assert aborted == ["/v2/actor-runs/run-slow/abort"]
    assert exc_info.value.run_data["id"] == "run-slow"
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
                        "usageTotalUsd": 0.01,
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
