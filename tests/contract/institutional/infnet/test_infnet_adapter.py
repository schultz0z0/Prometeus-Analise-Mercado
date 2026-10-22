"""Testes de contrato para o adaptador institucional da segunda instituição (Instituto Infnet)."""

import httpx
import pytest

from prometeus.infrastructure.institutional.infnet.client import (
    InfnetAuthenticationError,
    InfnetInstitutionalAdapter,
)

MOCK_INFNET_COURSES = [
    {
        "id": "INF-ENG-01",
        "titulo": "Bootcamp em Engenharia de Software e IA Generativa",
        "escola": "Escola de Computação",
        "formato": "online_ao_vivo",
        "carga_horaria": 480,
        "status_curso": "ativo",
        "publico_alvo": ["Desenvolvedores Plenos", "Engenheiros de Dados"],
        "habilidades": ["Python", "Docker", "LLMs", "RAG", "Cloud"],
    },
    {
        "id": "INF-CYBER-02",
        "titulo": "Especialização em Defesa Cibernética e DevSecOps",
        "escola": "Escola de Computação",
        "formato": "presencial",
        "carga_horaria": 360,
        "status_curso": "ativo",
        "publico_alvo": ["Analistas de Segurança", "DevOps Engineers"],
        "habilidades": ["SIEM", "Kubernetes", "SAST/DAST", "SOC"],
    },
]

MOCK_INFNET_FUNNEL = {
    "metricas": [
        {
            "curso_id": "INF-ENG-01",
            "semestre": "2026.1",
            "cadastros": 2000,
            "candidatos": 500,
            "matriculas": 150,
        }
    ]
}

MOCK_INFNET_FINANCIAL = {
    "financeiro": [
        {
            "curso_id": "INF-ENG-01",
            "semestre": "2026.1",
            "ticket_medio": 15000.0,
            "faturamento": 2250000.0,
            "cac": 850.0,
        }
    ]
}


def create_mock_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        auth = request.headers.get("Authorization")

        if "invalid-token" in (auth or ""):
            return httpx.Response(401, json={"error": "Unauthorized"})

        if "/cursos/INF-ENG-01" in url:
            return httpx.Response(200, json=MOCK_INFNET_COURSES[0])
        elif "/cursos/NON-EXISTENT" in url:
            return httpx.Response(404, json={"error": "Not Found"})
        elif "/cursos" in url:
            return httpx.Response(200, json={"items": MOCK_INFNET_COURSES})
        elif "/metricas/funil" in url:
            return httpx.Response(200, json=MOCK_INFNET_FUNNEL)
        elif "/metricas/financeiro" in url:
            return httpx.Response(200, json=MOCK_INFNET_FINANCIAL)
        elif "/health" in url:
            return httpx.Response(200, json={"status": "UP", "service": "Infnet-LMS"})

        return httpx.Response(404, json={"error": "Not Found"})

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_infnet_adapter_list_courses() -> None:
    transport = create_mock_transport()
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = InfnetInstitutionalAdapter(api_token="valid-token", http_client=client)
        courses = await adapter.list_courses()
        assert len(courses) == 2
        assert courses[0].external_id == "INF-ENG-01"
        assert courses[0].modality == "online"
        assert "LLMs" in courses[0].tags
        assert courses[1].external_id == "INF-CYBER-02"
        assert courses[1].modality == "presencial"


@pytest.mark.asyncio
async def test_infnet_adapter_get_course() -> None:
    transport = create_mock_transport()
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = InfnetInstitutionalAdapter(api_token="valid-token", http_client=client)
        course = await adapter.get_course("INF-ENG-01")
        assert course is not None
        assert course.name == "Bootcamp em Engenharia de Software e IA Generativa"
        assert course.workload_hours == 480

        not_found = await adapter.get_course("NON-EXISTENT")
        assert not_found is None


@pytest.mark.asyncio
async def test_infnet_adapter_funnel_and_financial() -> None:
    transport = create_mock_transport()
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = InfnetInstitutionalAdapter(api_token="valid-token", http_client=client)

        # Funil
        funnel = await adapter.get_funnel_metrics(["INF-ENG-01"], period="2026.1")
        assert len(funnel) == 1
        f = funnel[0]
        assert f.external_course_id == "INF-ENG-01"
        assert f.leads == 2000
        assert f.applicants == 500
        assert f.enrolled == 150
        assert f.conversion_lead_to_applicant == 0.25
        assert f.conversion_applicant_to_enrolled == 0.30
        assert f.conversion_lead_to_enrolled == 0.075

        # Financeiro
        financial = await adapter.get_financial_metrics(["INF-ENG-01"], period="2026.1")
        assert len(financial) == 1
        fin = financial[0]
        assert fin.average_ticket_brl == 15000.0
        assert fin.total_revenue_brl == 2250000.0
        assert fin.acquisition_cost_brl == 850.0


@pytest.mark.asyncio
async def test_infnet_adapter_healthcheck_and_auth_error() -> None:
    transport = create_mock_transport()
    async with httpx.AsyncClient(transport=transport) as client:
        # Sucesso
        adapter = InfnetInstitutionalAdapter(api_token="valid-token", http_client=client)
        health = await adapter.healthcheck()
        assert health.status == "ok"
        assert health.adapter_name == "infnet"

        # Falha de Autenticação
        auth_fail_adapter = InfnetInstitutionalAdapter(
            api_token="invalid-token", http_client=client
        )
        with pytest.raises(InfnetAuthenticationError):
            await auth_fail_adapter.list_courses()
