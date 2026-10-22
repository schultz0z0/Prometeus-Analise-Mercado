"""Portas e modelos canônicos para adaptadores de dados institucionais (CRMs educacionais).

Define contratos agnósticos para histórico interno, funil de conversão
e métricas de cursos sem acoplamento a schemas de fornecedores externos.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class CanonicalCourse:
    """Representação canônica e normalizada de um curso ofertado pela instituição."""

    external_id: str
    name: str
    category: str
    modality: str  # presencial, online, hibrido
    workload_hours: int
    status: str = "active"  # active, archived, draft
    target_audience: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FunnelMetrics:
    """Métricas agregadas do funil de admissão de um curso (minimização LGPD: sem PII)."""

    external_course_id: str
    period: str  # ex.: 2025-1, 2025-2, 2025-anual
    leads: int
    applicants: int  # inscritos
    enrolled: int  # matriculados
    conversion_lead_to_applicant: float = 0.0
    conversion_applicant_to_enrolled: float = 0.0
    conversion_lead_to_enrolled: float = 0.0

    def __post_init__(self) -> None:
        # Cálculo determinístico das taxas de conversão normalizadas
        lead_to_app = (self.applicants / self.leads) if self.leads > 0 else 0.0
        app_to_enr = (self.enrolled / self.applicants) if self.applicants > 0 else 0.0
        lead_to_enr = (self.enrolled / self.leads) if self.leads > 0 else 0.0

        object.__setattr__(self, "conversion_lead_to_applicant", round(lead_to_app, 4))
        object.__setattr__(self, "conversion_applicant_to_enrolled", round(app_to_enr, 4))
        object.__setattr__(self, "conversion_lead_to_enrolled", round(lead_to_enr, 4))


@dataclass(frozen=True)
class FinancialMetrics:
    """Métricas financeiras agregadas de um curso (opcional no CRM)."""

    external_course_id: str
    period: str
    average_ticket_brl: float
    total_revenue_brl: float
    acquisition_cost_brl: float | None = None


@dataclass
class HistoricalCourseAggregate:
    """Dossiê histórico consolidado de um curso para balizamento do pilar interno."""

    course: CanonicalCourse
    funnel_history: list[FunnelMetrics] = field(default_factory=list)
    financial_history: list[FinancialMetrics] = field(default_factory=list)
    data_quality_score: float = 1.0  # 0.0 a 1.0 (penalizado por campos nulos ou divergências)
    divergence_notes: list[str] = field(default_factory=list)
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class AdapterHealthStatus:
    """Estado de saúde e conectividade com a API do CRM institucional."""

    status: str  # ok, degraded, error
    adapter_name: str
    latency_ms: float
    message: str | None = None


class InstitutionalDataAdapter(ABC):
    """Porta canônica para conectores com CRMs acadêmicos (ENS, TOTVS, Salesforce, etc.)."""

    @abstractmethod
    async def list_courses(
        self,
        query: str | None = None,
        category: str | None = None,
        limit: int = 50,
        page: int = 1,
    ) -> list[CanonicalCourse]:
        """Lista cursos normalizados aplicando filtros opcionais de busca e categoria."""
        pass

    @abstractmethod
    async def get_course(self, course_id: str) -> CanonicalCourse | None:
        """Obtém os dados canônicos de um curso específico pelo ID externo."""
        pass

    @abstractmethod
    async def get_funnel_metrics(
        self,
        course_ids: list[str],
        period: str | None = None,
    ) -> list[FunnelMetrics]:
        """Obtém métricas agregadas de funil (leads, inscritos, matriculados)."""
        pass

    @abstractmethod
    async def get_financial_metrics(
        self,
        course_ids: list[str],
        period: str | None = None,
    ) -> list[FinancialMetrics]:
        """Obtém métricas financeiras agregadas caso suportado pelo conector."""
        pass

    @abstractmethod
    async def healthcheck(self) -> AdapterHealthStatus:
        """Verifica conectividade e prontidão da integração externa."""
        pass
