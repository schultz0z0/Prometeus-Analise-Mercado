import httpx
import pytest

from prometeus.domain.configuration import AppSettings
from prometeus.domain.research import PlannedToolCall
from prometeus.infrastructure.apify.client import ApifyClient, ApifyError
from prometeus.infrastructure.apify.registry import ApifyActorRegistry


def client_for(handler):
    settings = AppSettings(
        _env_file=None,
        APIFY_ACTOR_GOOGLE_SEARCH="apify/google-search-scraper@0.0.474",
    )
    return ApifyClient(
        api_token="test-only",
        registry=ApifyActorRegistry.from_settings(settings),
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        polling_interval_seconds=0,
    )


def call():
    return PlannedToolCall(
        id="billing",
        capability="google_search",
        query="curso seguros",
        rationale="test",
        max_items=1,
    )


def run_data(*, settled=False, status="SUCCEEDED"):
    return {
        "id": "run-billing",
        "status": status,
        "defaultDatasetId": "data-billing",
        "buildNumber": "0.0.474",
        "usageTotalUsd": 0.00455 if settled else 0.00005,
        "pricingInfo": {"pricingModel": "PAY_PER_EVENT"},
        "chargedEventCounts": {"start": 1, "page": 1},
        "accountedChargedEventCounts": {"start": 1, "page": int(settled)},
    }


async def test_successful_run_waits_for_accounting_without_buying_another_run():
    starts = 0
    reads = 0

    def handler(request):
        nonlocal starts, reads
        if request.method == "POST":
            starts += 1
            return httpx.Response(201, json={"data": run_data()})
        if "/actor-runs/" in request.url.path:
            reads += 1
            return httpx.Response(200, json={"data": run_data(settled=reads >= 2)})
        return httpx.Response(200, json=[{"title": "Curso", "url": "https://example.edu/curso"}])

    client = client_for(handler)
    try:
        result = await client.execute(call(), max_total_charge_usd=0.5)
    finally:
        await client.aclose()
    assert result.run.cost_usd == 0.00455
    assert starts == 1
    assert reads == 2


async def test_unsettled_billing_is_not_reported_as_a_known_tiny_cost():
    def handler(request):
        if request.method == "POST" or "/actor-runs/" in request.url.path:
            return httpx.Response(200, json={"data": run_data()})
        return httpx.Response(200, json=[])

    client = client_for(handler)
    try:
        with pytest.raises(ApifyError, match="[Cc]obrança") as error:
            await client.execute(call(), max_total_charge_usd=0.5)
        assert error.value.run_data["id"] == "run-billing"
    finally:
        await client.aclose()


async def test_polling_failure_preserves_remote_identity_for_reconciliation():
    def handler(request):
        if request.method == "POST":
            return httpx.Response(201, json={"data": run_data(status="RUNNING")})
        return httpx.Response(502, json={"error": "temporary provider failure"})

    client = client_for(handler)
    try:
        with pytest.raises(ApifyError, match="reconciliação") as error:
            await client.execute(call(), max_total_charge_usd=0.5)
        assert error.value.run_data["id"] == "run-billing"
    finally:
        await client.aclose()


async def test_dataset_failure_after_paid_run_keeps_remote_cost_and_identity():
    def handler(request):
        if request.method == "POST" or "/actor-runs/" in request.url.path:
            return httpx.Response(200, json={"data": run_data(settled=True)})
        return httpx.Response(502, json={"error": "dataset temporarily unavailable"})

    client = client_for(handler)
    try:
        with pytest.raises(ApifyError) as error:
            await client.execute(call(), max_total_charge_usd=0.5)
        assert error.value.run_data["id"] == "run-billing"
        assert error.value.run_data["usageTotalUsd"] == 0.00455
    finally:
        await client.aclose()


async def test_failed_actor_preserves_its_confirmed_nonzero_cost():
    def handler(request):
        return httpx.Response(200, json={"data": run_data(settled=True, status="FAILED")})

    client = client_for(handler)
    try:
        with pytest.raises(ApifyError) as error:
            await client.execute(call(), max_total_charge_usd=0.5)
        assert error.value.run_data["id"] == "run-billing"
        assert error.value.run_data["usageTotalUsd"] == 0.00455
    finally:
        await client.aclose()


async def test_billing_refresh_cannot_change_a_success_to_a_failed_result():
    def handler(request):
        if request.method == "POST":
            return httpx.Response(200, json={"data": run_data(settled=True)})
        if "/actor-runs/" in request.url.path:
            return httpx.Response(200, json={"data": run_data(settled=True, status="FAILED")})
        return httpx.Response(200, json=[])

    client = client_for(handler)
    try:
        with pytest.raises(ApifyError, match="estado"):
            await client.execute(call(), max_total_charge_usd=0.5)
    finally:
        await client.aclose()


async def test_missing_cost_after_terminal_failure_requires_reconciliation():
    from prometeus.infrastructure.apify.client import ApifyReconciliationRequiredError

    def handler(request):
        data = run_data(settled=True, status="FAILED")
        data.pop("pricingInfo")
        data.pop("usageTotalUsd")
        return httpx.Response(200, json={"data": data})

    client = client_for(handler)
    try:
        with pytest.raises(ApifyReconciliationRequiredError):
            await client.execute(call(), max_total_charge_usd=0.5)
    finally:
        await client.aclose()


@pytest.mark.parametrize("abort_status", ["ABORTING", "http_502"])
async def test_timeout_without_confirmed_abort_requires_reconciliation(abort_status):
    from prometeus.infrastructure.apify.client import ApifyReconciliationRequiredError

    def handler(request):
        data = run_data(status="RUNNING")
        if request.url.path.endswith("/abort"):
            if abort_status == "http_502":
                return httpx.Response(502)
            data["status"] = abort_status
        return httpx.Response(200, json={"data": data})

    client = client_for(handler)
    client.max_poll_attempts = 1
    try:
        with pytest.raises(ApifyReconciliationRequiredError) as error:
            await client.execute(call(), max_total_charge_usd=0.5)
        assert error.value.run_data["id"] == "run-billing"
        assert "não confirmado" in str(error.value)
    finally:
        await client.aclose()


async def test_partial_dataset_failure_preserves_the_reconciled_cost():
    aborted = False

    def handler(request):
        nonlocal aborted
        if request.url.path.endswith("/abort"):
            aborted = True
            data = run_data(status="ABORTED")
            data["usageTotalUsd"] = 0.13
            return httpx.Response(200, json={"data": data})
        if request.method == "POST" or "/actor-runs/" in request.url.path:
            data = run_data(settled=aborted, status="ABORTED" if aborted else "RUNNING")
            data["usageTotalUsd"] = 0.15 if aborted else 0.13
            return httpx.Response(200, json={"data": data})
        return httpx.Response(502)

    client = client_for(handler)
    client.max_poll_attempts = 1
    try:
        with pytest.raises(ApifyError) as error:
            await client.execute(call(), max_total_charge_usd=0.5)
        assert error.value.run_data["usageTotalUsd"] == 0.15
    finally:
        await client.aclose()


async def test_billing_refresh_keeps_verified_build_when_same_build_id_omits_number():
    def handler(request):
        data = run_data(settled=True)
        data.update({"buildNumber": None, "buildId": "verified-build", "actId": "actor-identity"})
        if "/actor-builds/" in request.url.path:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "id": "verified-build",
                        "actId": "actor-identity",
                        "buildNumber": "0.0.474",
                    }
                },
            )
        if request.method == "POST" or "/actor-runs/" in request.url.path:
            return httpx.Response(200, json={"data": data})
        return httpx.Response(200, json=[])

    client = client_for(handler)
    try:
        result = await client.execute(call(), max_total_charge_usd=0.5)
        assert result.run.build_number == "0.0.474"
    finally:
        await client.aclose()
