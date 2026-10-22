import pytest

from prometeus.infrastructure.institutional.mock import MockInstitutionalAdapter


async def test_mock_adapter_list_courses_and_filters() -> None:
    adapter = MockInstitutionalAdapter()

    # Sem filtros
    courses = await adapter.list_courses()
    assert len(courses) == 3

    # Filtro por texto / tag
    cyber_courses = await adapter.list_courses(query="cyber")
    assert len(cyber_courses) == 1
    assert cyber_courses[0].external_id == "ENS-SEG-02"

    # Filtro por categoria
    pos_courses = await adapter.list_courses(category="Pós-graduação")
    assert len(pos_courses) == 1
    assert pos_courses[0].external_id == "ENS-SEG-01"

    # Paginação
    page1 = await adapter.list_courses(limit=2, page=1)
    page2 = await adapter.list_courses(limit=2, page=2)
    assert len(page1) == 2
    assert len(page2) == 1
    assert page1[0].external_id != page2[0].external_id


async def test_mock_adapter_get_course_by_id() -> None:
    adapter = MockInstitutionalAdapter()
    course = await adapter.get_course("ENS-SEG-01")
    assert course is not None
    assert course.name == "MBA em Gestão de Seguros e Resseguros"
    assert course.workload_hours == 360

    non_existent = await adapter.get_course("NON-EXISTENT")
    assert non_existent is None


async def test_mock_adapter_funnel_and_financial_metrics() -> None:
    adapter = MockInstitutionalAdapter()
    funnel = await adapter.get_funnel_metrics(["ENS-SEG-01", "ENS-SEG-02"], period="2025-1")
    assert len(funnel) == 2

    m1 = next(m for m in funnel if m.external_course_id == "ENS-SEG-01")
    assert m1.leads == 1400
    assert m1.applicants == 280
    assert m1.enrolled == 98
    assert m1.conversion_lead_to_applicant == 0.20
    assert m1.conversion_applicant_to_enrolled == 0.35
    assert m1.conversion_lead_to_enrolled == 0.07

    financial = await adapter.get_financial_metrics(["ENS-SEG-01"], period="2025-1")
    assert len(financial) == 1
    assert financial[0].average_ticket_brl == 16500.00
    assert financial[0].total_revenue_brl == 1617000.00


async def test_mock_adapter_healthcheck_and_simulated_failure() -> None:
    # Caso saudável
    healthy_adapter = MockInstitutionalAdapter()
    health = await healthy_adapter.healthcheck()
    assert health.status == "ok"
    assert health.adapter_name == "mock"
    assert health.latency_ms >= 0

    # Caso com falha simulada
    failing_adapter = MockInstitutionalAdapter(simulate_failure=True)
    health_fail = await failing_adapter.healthcheck()
    assert health_fail.status == "error"

    with pytest.raises(ConnectionError):
        await failing_adapter.list_courses()
