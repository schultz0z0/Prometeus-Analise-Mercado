"""Modelos de dados canônicos e contratos de features do motor de scoring (Fase 05)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from prometeus.domain.analyses import AnalysisRecommendation


class PillarType(StrEnum):
    """Identificadores canônicos dos seis pilares de viabilidade."""

    INTERNAL_HISTORY = "internal_history"
    PAID_COMPETITION = "paid_competition"
    SEARCH_AND_MEDIA = "search_and_media"
    EMPLOYABILITY = "employability"
    SYLLABUS_FIT = "syllabus_fit"
    PRICING = "pricing"


@dataclass(frozen=True)
class PillarScore:
    """Pontuação e metadados de um pilar individual."""

    pillar_id: str
    raw_score: float  # [0.0, 100.0]
    weight: float  # [0.0, 1.0]
    confidence: float  # [0.0, 1.0]
    is_present: bool
    missing_reason: str | None = None
    features: dict[str, Any] = field(default_factory=dict)

    @property
    def weighted_score(self) -> float:
        """Retorna a contribuição ponderada do pilar se estiver presente."""
        return round(self.raw_score * self.weight, 4) if self.is_present else 0.0

    @property
    def weighted_confidence(self) -> float:
        """Retorna a confiança ponderada do pilar se estiver presente."""
        return round(self.confidence * self.weight, 4) if self.is_present else 0.0


class GateEvaluation(BaseModel):
    """Resultado detalhado da avaliação dos Quality Gates (Etapa 11)."""

    recommendation: AnalysisRecommendation
    passed_gates: bool
    viability_score: float
    coverage_score: float
    confidence_score: float
    reasons: list[str] = Field(default_factory=list)
    weighted_contribution: float | None = None
    observed_score: float | None = None
    score_blocks: dict[str, Any] = Field(default_factory=dict)
    profile_id: str = "default-v1"
    distance_to_approved_threshold: float = 0.0
    distance_to_adjustment_threshold: float = 0.0
    in_boundary_review_margin: bool = False


@dataclass(frozen=True)
class ScoringResult:
    """Resultado imutável completo do motor de viabilidade e calibração."""

    id: str
    analysis_id: str
    profile_id: str
    viability_score: float
    coverage_score: float
    confidence_score: float
    partial_score: float
    recommendation: AnalysisRecommendation
    pillar_scores: dict[str, PillarScore]
    gate_details: GateEvaluation
    is_experimental: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls,
        analysis_id: str,
        profile_id: str,
        viability_score: float,
        coverage_score: float,
        confidence_score: float,
        partial_score: float,
        recommendation: AnalysisRecommendation,
        pillar_scores: dict[str, PillarScore],
        gate_details: GateEvaluation,
        is_experimental: bool = True,
        result_id: str | None = None,
    ) -> ScoringResult:
        return cls(
            id=result_id or str(uuid.uuid4()),
            analysis_id=analysis_id,
            profile_id=profile_id,
            viability_score=round(viability_score, 2),
            coverage_score=round(coverage_score, 4),
            confidence_score=round(confidence_score, 4),
            partial_score=round(partial_score, 2),
            recommendation=recommendation,
            pillar_scores=pillar_scores,
            gate_details=gate_details,
            is_experimental=is_experimental,
        )
