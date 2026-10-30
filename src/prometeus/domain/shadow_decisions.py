"""Modelos de domínio para execução em Shadow Mode e avaliação de não inferioridade (Fase 6)."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

from prometeus.domain.ports.decision_model import DecisionType


class DivergenceCategory(StrEnum):
    """Categoria de divergência entre a decisão primária (produção) e a decisão shadow (JEV)."""

    CONCORDANT = "CONCORDANT"  # Mesma escolha / score compatível
    CONFIDENCE_DIVERGENCE = "CONFIDENCE_DIVERGENCE"  # Mesma escolha, mas confiança difere acima da tolerância
    CHOICE_DIVERGENCE = "CHOICE_DIVERGENCE"  # Escolhas diferentes
    SCORE_DIVERGENCE = "SCORE_DIVERGENCE"  # Scores numéricos diferem acima da tolerância
    ABSTENTION_DIVERGENCE = "ABSTENTION_DIVERGENCE"  # Um dos modelos absteve (NOUL/revisão) enquanto o outro decidiu
    SHADOW_ERROR = "SHADOW_ERROR"  # Erro de transporte, timeout ou falha na execução shadow


class ShadowComparisonRecord(BaseModel):
    """Registro de comparação lado a lado entre o modelo primário e o modelo shadow."""

    pack_id: str
    decision_type: DecisionType
    primary_model: str
    shadow_model: str
    primary_choice: str | None = None
    shadow_choice: str | None = None
    primary_score: float | None = None
    shadow_score: float | None = None
    primary_confidence: float = 0.0
    shadow_confidence: float = 0.0
    primary_is_noul: bool = False
    shadow_is_noul: bool = False
    is_concordant: bool = True
    divergence_category: DivergenceCategory = DivergenceCategory.CONCORDANT
    divergence_notes: str | None = None
    primary_latency_ms: float = 0.0
    shadow_latency_ms: float = 0.0
    primary_cost_usd: float | None = None
    shadow_cost_usd: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class TaskNonInferiorityCriteria(BaseModel):
    """Critérios acordados de não inferioridade por tarefa/pack antes da homologação."""

    pack_id: str
    minimum_agreement_rate: float = 0.90  # Acordo mínimo de 90%
    maximum_abstention_rate: float = 0.15  # Máximo de 15% de abstenção (NOUL)
    maximum_latency_p95_ms: float = 2000.0  # Limite de latência P95
    calibration_tolerance: float = 0.15  # Diferença aceitável de calibração
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"


class NonInferiorityEvaluation(BaseModel):
    """Resultado da avaliação formal de não inferioridade para um decision pack."""

    pack_id: str
    total_evaluations: int
    concordant_count: int
    agreement_rate: float
    shadow_abstention_rate: float
    primary_abstention_rate: float
    latency_delta_mean_ms: float
    divergence_counts: dict[str, int]
    criteria: TaskNonInferiorityCriteria
    verdict: Literal["APPROVED_FOR_HYBRID", "RETAIN_TRADITIONAL"]
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

