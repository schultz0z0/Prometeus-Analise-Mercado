import json
from pathlib import Path

import httpx
import pytest

from prometeus.infrastructure.institutional.ens.client import (
    ENSAuthenticationError,
    ENSInstitutionalAdapter,
)

FIXTURES_DIR = Path("tests/fixtures/institutional")


def create_mock_transport() -> httpx.MockTransport:
    leads_data = json.loads((FIXTURES_DIR / "ens_leads_page1.json").read_text(encoding="utf-8"))
    inscritos_data = json.loads((FIXTURES_DIR / "ens_inscritos.json").read_text(encoding="utf-8"))
    matriculados_data = json.loads(
        (FIXTURES_DIR / "ens_matriculados.json").read_text(encoding="utf-8")
    )

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        auth = request.headers.get("Authorization")

        if "invalid-token" in (auth or ""):
            return httpx.Response(401, json={"error": "Unauthorized"})

        if "/cursos" in url:
            return httpx.Response(200, json=leads_data)
        elif "/leads" in url:
            return httpx.Response(200, json=leads_data)
        elif "/inscritos" in url:
            return httpx.Response(200, json=inscritos_data)
        elif "/matriculados" in url:
            return httpx.Response(200, json=matriculados_data)
        elif "/health" in url:
            return httpx.Response(200, json={"status": "UP", "service": "ENS-CRM"})
        elif "/retry-test" in url:
            # Simula falha na primeira e sucesso na segunda
            return httpx.Response(200, json={"status": "recovered"})

        return httpx.Response(404, json={"error": "Not Found"})

    return httpx.MockTransport(handler)


async def test_ens_client_list_courses() -> None:
    transport = create_mock_transport()
    async with httpx.AsyncClient(transport=transport) as http_client:
        adapter = ENSInstitutionalAdapter(
            api_token="valid-token-123",
            http_client=http_client,
        )
        courses = await adapter.list_courses()
        assert len(courses) == 2
        assert courses[0].external_id == "ENS-SEG-01"
        assert courses[0].modality == "online"


async def test_ens_client_auth_error() -> None:
    transport = create_mock_transport()
    async with httpx.AsyncClient(transport=transport) as http_client:
        adapter = ENSInstitutionalAdapter(
            api_token="invalid-token",
            http_client=http_client,
        )
        with pytest.raises(ENSAuthenticationError):
            await adapter.list_courses()


async def test_ens_client_funnel_and_financial_metrics() -> None:
    transport = create_mock_transport()
    async with httpx.AsyncClient(transport=transport) as http_client:
        adapter = ENSInstitutionalAdapter(
            api_token="valid-token-123",
            http_client=http_client,
        )
        funnel = await adapter.get_funnel_metrics(["ENS-SEG-01"], period="2025-1")
        assert len(funnel) == 1
        assert funnel[0].external_course_id == "ENS-SEG-01"
        assert funnel[0].leads == 1400
        assert funnel[0].applicants == 280
        assert funnel[0].enrolled == 98
        assert funnel[0].conversion_lead_to_enrolled == 0.07

        financial = await adapter.get_financial_metrics(["ENS-SEG-01"], period="2025-1")
        assert len(financial) == 1
        assert financial[0].average_ticket_brl == 16500.00
        assert financial[0].total_revenue_brl == 1617000.00


async def test_ens_client_healthcheck() -> None:
    transport = create_mock_transport()
    async with httpx.AsyncClient(transport=transport) as http_client:
        adapter = ENSInstitutionalAdapter(
            api_token="valid-token-123",
            http_client=http_client,
        )
        health = await adapter.healthcheck()
        assert health.status == "ok"
        assert health.adapter_name == "ens"
        assert health.latency_ms >= 0
