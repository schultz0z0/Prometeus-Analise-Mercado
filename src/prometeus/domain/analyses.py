"""Domínio de análises de viabilidade e inteligência educacional.

Implementa a máquina de estados e invariantes do ADR-0005.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class AnalysisStatus(StrEnum):
    """Ciclo de vida da análise (ADR-0005)."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_FOR_INPUT = "WAITING_FOR_INPUT"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AnalysisRecommendation(StrEnum):
    """Resultado do motor determinístico (ADR-0005)."""

    APPROVED = "APPROVED"
    APPROVED_WITH_ADJUSTMENTS = "APPROVED_WITH_ADJUSTMENTS"
    HIGH_RISK = "HIGH_RISK"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    REQUIRES_HUMAN_REVIEW = "REQUIRES_HUMAN_REVIEW"


TERMINAL_STATUSES = {
    AnalysisStatus.COMPLETED,
    AnalysisStatus.FAILED,
    AnalysisStatus.CANCELLED,
}

# Mapa estrito de transições válidas conforme ADR-0005
ALLOWED_TRANSITIONS: dict[AnalysisStatus, set[AnalysisStatus]] = {
    AnalysisStatus.QUEUED: {AnalysisStatus.RUNNING, AnalysisStatus.CANCELLED},
    AnalysisStatus.RUNNING: {
        AnalysisStatus.WAITING_FOR_INPUT,
        AnalysisStatus.BLOCKED,
        AnalysisStatus.COMPLETED,
        AnalysisStatus.FAILED,
        AnalysisStatus.CANCELLED,
    },
    AnalysisStatus.WAITING_FOR_INPUT: {
        AnalysisStatus.RUNNING,
        AnalysisStatus.CANCELLED,
    },
    AnalysisStatus.BLOCKED: {
        AnalysisStatus.RUNNING,
        AnalysisStatus.FAILED,
        AnalysisStatus.CANCELLED,
    },
    AnalysisStatus.COMPLETED: set(),
    AnalysisStatus.FAILED: set(),
    AnalysisStatus.CANCELLED: set(),
}


class DomainError(Exception):
    """Exceção base de regras de negócio."""

    pass


class InvalidStateTransitionError(DomainError):
    """Lançada quando se tenta executar uma transição de estado não permitida pelo ADR-0005."""

    pass


class InvalidRecommendationError(DomainError):
    """Lançada quando se tenta definir ou consultar recomendação fora do estado COMPLETED."""

    pass


@dataclass
class AuditEvent:
    """Registro auditável e imutável de transição de estado (ADR-0005)."""

    id: str
    analysis_id: str
    from_status: AnalysisStatus | None
    to_status: AnalysisStatus
    reason: str | None
    correlation_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class AnalysisStep:
    """Etapa de execução do workflow (ADR-0004)."""

    id: str
    analysis_id: str
    step_number: int
    name: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    output_summary: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


@dataclass
class Analysis:
    """Raiz de agregação representando uma solicitação e dossiê de viabilidade educacional."""

    id: str
    tenant_id: str
    course_name: str
    proposal_data: dict[str, Any]
    status: AnalysisStatus
    recommendation: AnalysisRecommendation | None
    created_at: datetime
    updated_at: datetime
    previous_analysis_id: str | None = None
    audit_events: list[AuditEvent] = field(default_factory=list)
    steps: list[AnalysisStep] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        tenant_id: str,
        course_name: str,
        correlation_id: str,
        proposal_data: dict[str, Any] | None = None,
        analysis_id: str | None = None,
        previous_analysis_id: str | None = None,
    ) -> Analysis:
        """Cria uma nova análise no estado inicial QUEUED com recomendação nula."""
        now = datetime.now(UTC)
        uid = analysis_id or str(uuid.uuid4())
        initial_event = AuditEvent(
            id=str(uuid.uuid4()),
            analysis_id=uid,
            from_status=None,
            to_status=AnalysisStatus.QUEUED,
            reason="Análise aceita e enfileirada",
            correlation_id=correlation_id,
            created_at=now,
        )

        return cls(
            id=uid,
            tenant_id=tenant_id,
            course_name=course_name,
            proposal_data=proposal_data or {},
            status=AnalysisStatus.QUEUED,
            recommendation=None,
            previous_analysis_id=previous_analysis_id,
            created_at=now,
            updated_at=now,
            audit_events=[initial_event],
            steps=[],
        )

    @property
    def is_terminal(self) -> bool:
        """Retorna True se o estado atual for terminal (COMPLETED, FAILED, CANCELLED)."""
        return self.status in TERMINAL_STATUSES

    def _transition_to(
        self,
        new_status: AnalysisStatus,
        correlation_id: str,
        reason: str | None = None,
    ) -> None:
        """Executa a transição de estado validando invariantes e emitindo evento de auditoria."""
        if self.is_terminal:
            raise InvalidStateTransitionError(
                f"Estado terminal '{self.status.value}' não permite transição para '{new_status.value}'."
            )

        allowed = ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise InvalidStateTransitionError(
                f"Transição inválida: de '{self.status.value}' para '{new_status.value}'. "
                f"Permitidas: {[s.value for s in allowed]}"
            )

        now = datetime.now(UTC)
        event = AuditEvent(
            id=str(uuid.uuid4()),
            analysis_id=self.id,
            from_status=self.status,
            to_status=new_status,
            reason=reason,
            correlation_id=correlation_id,
            created_at=now,
        )
        self.status = new_status
        self.updated_at = now
        self.audit_events.append(event)

    def start(self, correlation_id: str, reason: str = "Início do processamento em worker") -> None:
        """Transiciona de QUEUED para RUNNING."""
        self._transition_to(AnalysisStatus.RUNNING, correlation_id=correlation_id, reason=reason)

    def wait_for_input(
        self, correlation_id: str, reason: str = "Aguardando entrada adicional"
    ) -> None:
        """Transiciona de RUNNING para WAITING_FOR_INPUT."""
        self._transition_to(
            AnalysisStatus.WAITING_FOR_INPUT, correlation_id=correlation_id, reason=reason
        )

    def block(self, correlation_id: str, reason: str = "Bloqueado por dependência externa") -> None:
        """Transiciona de RUNNING para BLOCKED por indisponibilidade externa recuperável."""
        self._transition_to(AnalysisStatus.BLOCKED, correlation_id=correlation_id, reason=reason)

    def resume(self, correlation_id: str, reason: str = "Retomada da execução") -> None:
        """Transiciona de WAITING_FOR_INPUT ou BLOCKED para RUNNING."""
        self._transition_to(AnalysisStatus.RUNNING, correlation_id=correlation_id, reason=reason)

    def complete(
        self,
        recommendation: AnalysisRecommendation,
        correlation_id: str,
        reason: str = "Dossiê finalizado com sucesso",
    ) -> None:
        """Transiciona para COMPLETED com preenchimento obrigatório da recomendação."""
        if not recommendation or not isinstance(recommendation, AnalysisRecommendation):
            raise InvalidRecommendationError(
                "A conclusão de uma análise exige uma recomendação válida do motor determinístico."
            )

        self._transition_to(AnalysisStatus.COMPLETED, correlation_id=correlation_id, reason=reason)
        self.recommendation = recommendation

    def fail(self, correlation_id: str, reason: str = "Falha não recuperável") -> None:
        """Transiciona para FAILED devido a erro irrecuperável."""
        self._transition_to(AnalysisStatus.FAILED, correlation_id=correlation_id, reason=reason)

    def cancel(
        self, correlation_id: str, reason: str = "Cancelada pelo usuário ou sistema"
    ) -> None:
        """Cancela a análise antes da conclusão."""
        self._transition_to(AnalysisStatus.CANCELLED, correlation_id=correlation_id, reason=reason)

    def set_recommendation(self, recommendation: AnalysisRecommendation) -> None:
        """Permite alterar a recomendação apenas quando a análise estiver COMPLETED."""
        if self.status != AnalysisStatus.COMPLETED:
            raise InvalidRecommendationError(
                f"Recomendação só pode ser atribuída quando status == COMPLETED. Status atual: {self.status.value}"
            )
        self.recommendation = recommendation
