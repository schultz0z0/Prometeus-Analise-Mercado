"""Adaptador institucional Mock para testes locais, CI e desenvolvimento offline."""

from __future__ import annotations

import time

from prometeus.domain.ports.institutional_data import (
    AdapterHealthStatus,
    CanonicalCourse,
    FinancialMetrics,
    FunnelMetrics,
    InstitutionalDataAdapter,
)

DEFAULT_MOCK_COURSES = [
    CanonicalCourse(
        external_id="ENS-SEG-01",
        name="MBA em Gestão de Seguros e Resseguros",
        category="Pós-graduação",
        modality="online",
        workload_hours=360,
        status="active",
        target_audience=["Gerentes de seguradoras", "Corretores de grande porte"],
        tags=["seguros", "resseguros", "gestao", "mba"],
    ),
    CanonicalCourse(
        external_id="ENS-SEG-02",
        name="Especialização em Subscrição de Riscos Cibernéticos",
        category="Extensão",
        modality="online",
        workload_hours=120,
        status="active",
        target_audience=["Subscritores", "Analistas de segurança da informação"],
        tags=["cyber", "riscos", "subscricao"],
    ),
    CanonicalCourse(
        external_id="ENS-SEG-03",
        name="Certificação Técnica em Regulação de Sinistros",
        category="Certificação",
        modality="presencial",
        workload_hours=60,
        status="active",
        target_audience=["Peritos", "Reguladores de sinistros"],
        tags=["sinistros", "regulacao", "pericia"],
    ),
]

DEFAULT_MOCK_FUNNEL = {
    "ENS-SEG-01": FunnelMetrics(
        external_course_id="ENS-SEG-01",
        period="2025-1",
        leads=1400,
        applicants=280,
        enrolled=98,
    ),
    "ENS-SEG-02": FunnelMetrics(
        external_course_id="ENS-SEG-02",
        period="2025-1",
        leads=850,
        applicants=170,
        enrolled=62,
    ),
    "ENS-SEG-03": FunnelMetrics(
        external_course_id="ENS-SEG-03",
        period="2025-1",
        leads=420,
        applicants=95,
        enrolled=45,
    ),
}

DEFAULT_MOCK_FINANCIAL = {
    "ENS-SEG-01": FinancialMetrics(
        external_course_id="ENS-SEG-01",
        period="2025-1",
        average_ticket_brl=16500.00,
        total_revenue_brl=1617000.00,
        acquisition_cost_brl=125.00,
    ),
    "ENS-SEG-02": FinancialMetrics(
        external_course_id="ENS-SEG-02",
        period="2025-1",
        average_ticket_brl=9800.00,
        total_revenue_brl=607600.00,
        acquisition_cost_brl=110.00,
    ),
    "ENS-SEG-03": FinancialMetrics(
        external_course_id="ENS-SEG-03",
        period="2025-1",
        average_ticket_brl=4500.00,
        total_revenue_brl=202500.00,
        acquisition_cost_brl=85.00,
    ),
}


class MockInstitutionalAdapter(InstitutionalDataAdapter):
    """Adaptador de dados que simula com exatidão os contratos institucionais."""

    def __init__(
        self,
        courses: list[CanonicalCourse] | None = None,
        funnel_data: dict[str, FunnelMetrics] | None = None,
        financial_data: dict[str, FinancialMetrics] | None = None,
        simulate_failure: bool = False,
    ) -> None:
        self.courses = courses if courses is not None else list(DEFAULT_MOCK_COURSES)
        self.funnel_data = funnel_data if funnel_data is not None else dict(DEFAULT_MOCK_FUNNEL)
        self.financial_data = (
            financial_data if financial_data is not None else dict(DEFAULT_MOCK_FINANCIAL)
        )
        self.simulate_failure = simulate_failure

    async def list_courses(
        self,
        query: str | None = None,
        category: str | None = None,
        limit: int = 50,
        page: int = 1,
    ) -> list[CanonicalCourse]:
        if self.simulate_failure:
            raise ConnectionError("Simulação de falha de conexão com CRM")

        filtered = self.courses
        if query:
            q = query.strip().lower()
            filtered = [
                c
                for c in filtered
                if q in c.name.lower() or any(q in tag.lower() for tag in c.tags)
            ]

        if category:
            cat = category.strip().lower()
            filtered = [c for c in filtered if c.category.lower() == cat]

        # Paginação
        start = (page - 1) * limit
        end = start + limit
        return filtered[start:end]

    async def get_course(self, course_id: str) -> CanonicalCourse | None:
        if self.simulate_failure:
            raise ConnectionError("Simulação de falha de conexão com CRM")

        for c in self.courses:
            if c.external_id == course_id:
                return c
        return None

    async def get_funnel_metrics(
        self,
        course_ids: list[str],
        period: str | None = None,
    ) -> list[FunnelMetrics]:
        if self.simulate_failure:
            raise ConnectionError("Simulação de falha de conexão com CRM")

        results: list[FunnelMetrics] = []
        for cid in course_ids:
            metric = self.funnel_data.get(cid)
            if metric and (period is None or metric.period == period):
                results.append(metric)
        return results

    async def get_financial_metrics(
        self,
        course_ids: list[str],
        period: str | None = None,
    ) -> list[FinancialMetrics]:
        if self.simulate_failure:
            raise ConnectionError("Simulação de falha de conexão com CRM")

        results: list[FinancialMetrics] = []
        for cid in course_ids:
            fin = self.financial_data.get(cid)
            if fin and (period is None or fin.period == period):
                results.append(fin)
        return results

    async def healthcheck(self) -> AdapterHealthStatus:
        start_time = time.perf_counter()
        if self.simulate_failure:
            return AdapterHealthStatus(
                status="error",
                adapter_name="mock",
                latency_ms=10.0,
                message="Adaptador configurado em modo de falha simulada",
            )
        elapsed = (time.perf_counter() - start_time) * 1000.0
        return AdapterHealthStatus(
            status="ok",
            adapter_name="mock",
            latency_ms=round(elapsed, 2),
            message="Mock operacional com dados sintéticos ativos",
        )
