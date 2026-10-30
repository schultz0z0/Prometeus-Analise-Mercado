import httpx
import pytest

from prometeus.domain.configuration import AppSettings
from prometeus.domain.research import PlannedToolCall
from prometeus.infrastructure.apify.client import (
    ApifyClient,
    ApifySchemaDriftError,
    ApifyTimeoutError,
)
from prometeus.infrastructure.apify.registry import ApifyActorRegistry
from prometeus.infrastructure.apify.schemas import validate_dataset_items


def test_instagram_no_items_is_a_provider_observation_not_schema_drift():
    marker = {"error": "no_items", "errorDescription": "Empty or private data for provided input"}
    assert validate_dataset_items("instagram", [marker]) == [marker]
    with pytest.raises(ValueError):
        validate_dataset_items("instagram", [{"unrecognized": "data"}])


@pytest.mark.parametrize("abort_status", ["ABORTED", "ABORTING", "RUNNING"])
async def test_timeout_reads_partial_dataset_only_after_confirmed_terminal_abort(abort_status):
    requests = []

    def handler(request):
        requests.append(request)
        if "/datasets/" in request.url.path:
            return httpx.Response(
                200,
                json=[
                    {
                        "searchTerm": "seguros",
                        "interestOverTime_timelineData": [{"value": [20], "hasData": [True]}],
                    }
                ],
            )
        return httpx.Response(
            200,
            json={
                "data": {
                    "id": "run-partial",
                    "status": abort_status if request.url.path.endswith("/abort") else "RUNNING",
                    "defaultDatasetId": "dataset-partial",
                    "buildNumber": "0.0.143",
                    "usageTotalUsd": 0.13,
                }
            },
        )

    registry = ApifyActorRegistry.from_settings(
        AppSettings(_env_file=None, APIFY_ACTOR_GOOGLE_TRENDS="apify/google-trends-scraper@0.0.143")
    )
    client = ApifyClient(
        api_token="test",
        registry=registry,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        polling_interval_seconds=0,
        max_poll_attempts=1,
    )
    call = PlannedToolCall(
        id="trends", capability="google_trends", query="seguros", rationale="test", max_items=5
    )
    try:
        if abort_status == "ABORTED":
            result = await client.execute(call, max_total_charge_usd=1)
            assert result.run.status == "ABORTED"
            assert result.run.incomplete_reason
            assert result.run.cost_usd == 0.13
            assert len(result.items) == 1
        else:
            with pytest.raises(ApifyTimeoutError):
                await client.execute(call, max_total_charge_usd=1)
            assert not any("/datasets/" in r.url.path for r in requests)
    finally:
        await client.aclose()


async def test_partial_run_with_wrong_build_is_rejected_with_operational_metadata():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "data": {
                    "id": "wrong-build",
                    "status": "ABORTED" if request.url.path.endswith("/abort") else "RUNNING",
                    "defaultDatasetId": "dataset",
                    "buildNumber": "0.0.999",
                    "usageTotalUsd": 0.13,
                }
            },
        )

    registry = ApifyActorRegistry.from_settings(
        AppSettings(_env_file=None, APIFY_ACTOR_GOOGLE_TRENDS="apify/google-trends-scraper@0.0.143")
    )
    client = ApifyClient(
        api_token="test",
        registry=registry,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        polling_interval_seconds=0,
        max_poll_attempts=1,
    )
    call = PlannedToolCall(
        id="trends", capability="google_trends", query="seguros", rationale="test", max_items=5
    )
    try:
        with pytest.raises(ApifySchemaDriftError) as error:
            await client.execute(call, max_total_charge_usd=1)
        assert error.value.run_data["id"] == "wrong-build"
        assert error.value.run_data["usageTotalUsd"] == 0.13
    finally:
        await client.aclose()


@pytest.mark.parametrize("refreshed_build", ["0.0.143", "0.0.999", None])
async def test_aborted_run_missing_build_number_is_reconciled_without_guessing(refreshed_build):
    polls = 0
    paths = []

    def handler(request):
        nonlocal polls
        paths.append(request.url.path)
        if "/datasets/" in request.url.path:
            return httpx.Response(
                200,
                json=[
                    {
                        "searchTerm": "seguros",
                        "interestOverTime_timelineData": [{"value": [20], "hasData": [True]}],
                    }
                ],
            )
        if "/actor-builds/" in request.url.path:
            return httpx.Response(
                200,
                json={
                    "data": {"id": "build-real", "actId": "actor-real", "buildNumber": "0.0.143"}
                },
            )
        if request.method == "GET":
            polls += 1
        aborted = request.url.path.endswith("/abort")
        terminal = aborted or polls > 1
        return httpx.Response(
            200,
            json={
                "data": {
                    "id": "run-real",
                    "actId": "actor-real",
                    "status": "ABORTED" if terminal else "RUNNING",
                    "defaultDatasetId": "dataset-real",
                    "buildId": "build-real",
                    "buildNumber": None if aborted else refreshed_build if terminal else "0.0.143",
                    "usageTotalUsd": 0.148328,
                }
            },
        )

    registry = ApifyActorRegistry.from_settings(
        AppSettings(_env_file=None, APIFY_ACTOR_GOOGLE_TRENDS="apify/google-trends-scraper@0.0.143")
    )
    client = ApifyClient(
        api_token="test",
        registry=registry,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        polling_interval_seconds=0,
        max_poll_attempts=1,
    )
    call = PlannedToolCall(
        id="trends", capability="google_trends", query="seguros", rationale="test", max_items=5
    )
    try:
        if refreshed_build == "0.0.999":
            with pytest.raises(ApifySchemaDriftError):
                await client.execute(call, max_total_charge_usd=1)
            assert not any("/datasets/" in p for p in paths)
        else:
            result = await client.execute(call, max_total_charge_usd=1)
            assert result.run.build_number == "0.0.143"
            assert result.run.cost_usd == 0.148328
            assert result.run.status == "ABORTED"
            assert result.run.incomplete_reason
    finally:
        await client.aclose()


@pytest.mark.parametrize("bad_identity", ["run", "build", "actor"])
async def test_build_reconciliation_rejects_mismatched_identity_and_keeps_cost(bad_identity):
    paths = []

    def handler(request):
        paths.append(request.url.path)
        if "/actor-builds/" in request.url.path:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "id": "wrong" if bad_identity == "build" else "build-real",
                        "actId": "wrong" if bad_identity == "actor" else "actor-real",
                        "buildNumber": "0.0.143",
                    }
                },
            )
        return httpx.Response(
            200,
            json={
                "data": {
                    "id": "wrong"
                    if request.method == "GET" and bad_identity == "run"
                    else "run-real",
                    "status": "SUCCEEDED",
                    "actId": "actor-real",
                    "buildId": "build-real",
                    "buildNumber": None,
                    "defaultDatasetId": "dataset-real",
                    "usageTotalUsd": 0.15,
                }
            },
        )

    registry = ApifyActorRegistry.from_settings(
        AppSettings(_env_file=None, APIFY_ACTOR_GOOGLE_TRENDS="apify/google-trends-scraper@0.0.143")
    )
    client = ApifyClient(
        api_token="test",
        registry=registry,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        max_poll_attempts=1,
    )
    call = PlannedToolCall(
        id="trends", capability="google_trends", query="seguros", rationale="test", max_items=5
    )
    try:
        with pytest.raises(ApifySchemaDriftError) as error:
            await client.execute(call, max_total_charge_usd=1)
        assert error.value.run_data["usageTotalUsd"] == 0.15
        assert error.value.run_data["id"] == "run-real"
        assert not any("/datasets/" in p for p in paths)
    finally:
        await client.aclose()
