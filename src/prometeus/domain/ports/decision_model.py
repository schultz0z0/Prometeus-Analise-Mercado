"""Portas e modelos canônicos para modelos de decisão atômica (JEV / TypeSafe AI).

Implementa os tipos fundamentais Choice, Score e Noul com desacoplamento
estrito do SDK do fornecedor (ADR-0003).
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DecisionType(StrEnum):
    """Tipos canônicos de julgamento suportados pelo JEV."""

    CHOICE = "CHOICE"
    SCORE = "SCORE"
    NOUL = "NOUL"


class DecisionPack(BaseModel):
    """Especificação e governança de um Decision Pack delimitado."""

    schema_version: int = 1
    pack_id: str
    version: str = "1.0.0"
    owner: str = "Agência Prometeus"
    decision_type: DecisionType
    question: str
    options: list[str] = Field(default_factory=list)
    min_score: float = 0.0
    max_score: float = 100.0
    rubric: dict[str, str] = Field(default_factory=dict)
    review_threshold: float = 0.75  # Confiança abaixo deste limiar exige revisão humana
    notes: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class DecisionResult:
    """Resultado imutável de uma execução atômica do JEV."""

    id: str
    pack_id: str
    decision_type: DecisionType
    confidence: float
    is_noul: bool = False
    selected_choice: str | None = None
    distribution: dict[str, float] = field(default_factory=dict)
    score_value: float | None = None
    requires_human_review: bool = False
    evidence_ids: list[str] = field(default_factory=list)
    model_version: str = "jev-pinned"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def choice(
        cls,
        pack_id: str,
        selected: str,
        confidence: float,
        distribution: dict[str, float] | None = None,
        review_threshold: float = 0.75,
        evidence_ids: list[str] | None = None,
        model_version: str = "jev-pinned",
    ) -> DecisionResult:
        """Cria resultado de decisão Choice com avaliação de limiar de revisão."""
        req_review = confidence < review_threshold
        return cls(
            id=str(uuid.uuid4()),
            pack_id=pack_id,
            decision_type=DecisionType.CHOICE,
            confidence=round(confidence, 4),
            is_noul=False,
            selected_choice=selected,
            distribution=distribution or {},
            score_value=None,
            requires_human_review=req_review,
            evidence_ids=evidence_ids or [],
            model_version=model_version,
        )

    @classmethod
    def score(
        cls,
        pack_id: str,
        value: float,
        confidence: float,
        review_threshold: float = 0.75,
        evidence_ids: list[str] | None = None,
        model_version: str = "jev-pinned",
    ) -> DecisionResult:
        """Cria resultado de decisão Score com avaliação de limiar de revisão."""
        req_review = confidence < review_threshold
        return cls(
            id=str(uuid.uuid4()),
            pack_id=pack_id,
            decision_type=DecisionType.SCORE,
            confidence=round(confidence, 4),
            is_noul=False,
            selected_choice=None,
            distribution={},
            score_value=round(value, 2),
            requires_human_review=req_review,
            evidence_ids=evidence_ids or [],
            model_version=model_version,
        )

    @classmethod
    def noul(
        cls,
        pack_id: str,
        reason: str,
        evidence_ids: list[str] | None = None,
        model_version: str = "jev-pinned",
    ) -> DecisionResult:
        """Cria resultado Noul (evidência insuficiente ou inconclusiva; sempre exige revisão)."""
        return cls(
            id=str(uuid.uuid4()),
            pack_id=pack_id,
            decision_type=DecisionType.NOUL,
            confidence=0.0,
            is_noul=True,
            selected_choice=None,
            distribution={},
            score_value=None,
            requires_human_review=True,
            evidence_ids=evidence_ids or [],
            model_version=model_version,
        )


class DecisionModelPort(ABC):
    """Porta agnóstica para motores de julgamento JEV."""

    @abstractmethod
    async def execute_choice(
        self,
        pack: DecisionPack,
        context: dict[str, Any],
        evidence_ids: list[str] | None = None,
    ) -> DecisionResult:
        """Executa um julgamento do tipo Choice."""
        pass

    @abstractmethod
    async def execute_score(
        self,
        pack: DecisionPack,
        context: dict[str, Any],
        evidence_ids: list[str] | None = None,
    ) -> DecisionResult:
        """Executa um julgamento do tipo Score."""
        pass
