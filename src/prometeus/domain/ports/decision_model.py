"""Portas e modelos canônicos para modelos de decisão atômica (JEV / TypeSafe AI).

Implementa os tipos fundamentais Choice, Score e Noul com desacoplamento
estrito do SDK do fornecedor (ADR-0003).
"""

from __future__ import annotations

import math
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def validate_probability(value: Any, field_name: str = "confidence") -> float:
    """Valida probabilidade estrita: não booleano, número finito entre 0.0 e 1.0."""
    if isinstance(value, bool):
        raise ValueError(f"'{field_name}' não pode ser um booleano.")
    if value is None:
        raise ValueError(f"'{field_name}' é obrigatório.")
    try:
        val = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"'{field_name}' deve ser um número válido: {exc}") from exc
    if not math.isfinite(val):
        raise ValueError(f"'{field_name}' deve ser um número finito.")
    if not (0.0 <= val <= 1.0):
        raise ValueError(f"'{field_name}' deve estar entre 0.0 e 1.0.")
    return val


def validate_finite_number(
    value: Any,
    field_name: str,
    min_val: float,
    max_val: float,
) -> float:
    """Valida número finito estrito dentro da escala permitida."""
    if isinstance(value, bool):
        raise ValueError(f"'{field_name}' não pode ser um booleano.")
    if value is None:
        raise ValueError(f"'{field_name}' é obrigatório.")
    try:
        val = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"'{field_name}' deve ser um número válido: {exc}") from exc
    if not math.isfinite(val):
        raise ValueError(f"'{field_name}' deve ser um número finito.")
    if not (min_val <= val <= max_val):
        raise ValueError(f"O {field_name} {val} está fora da escala {min_val}..{max_val}.")
    return val


def validate_choice_selection(choice: Any, allowed_options: list[str], pack_id: str) -> str:
    """Valida que choice é string não vazia e pertence às opções permitidas do pack."""
    if not choice or not isinstance(choice, str):
        raise ValueError(f"A resposta de decisão não contém 'selected_choice' válido para o pack '{pack_id}'.")
    choice_str = choice.strip()
    if choice_str not in allowed_options:
        raise ValueError(
            f"A LLM retornou a opção não permitida '{choice_str}' para o pack '{pack_id}'."
        )
    return choice_str


def validate_distribution(
    distribution: Any, allowed_options: list[str]
) -> dict[str, float]:
    """Valida distribuição: dicionário com chaves permitidas, probabilidades válidas e soma coerente."""
    if not isinstance(distribution, dict):
        raise ValueError("A resposta estruturada não contém 'distribution' válido.")
    cleaned: dict[str, float] = {}
    for key, prob in distribution.items():
        key_str = str(key).strip()
        if key_str not in allowed_options:
            raise ValueError(f"Opção desconhecida '{key_str}' na distribuição de probabilidades.")
        cleaned[key_str] = validate_probability(prob, f"distribuição[{key_str}]")
    if cleaned:
        total = sum(cleaned.values())
        if not math.isclose(total, 1.0, abs_tol=0.15):
            raise ValueError(f"A soma da distribuição de probabilidades ({total:.3f}) é inválida.")
    return cleaned


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


@dataclass(frozen=True)
class ModelIdentity:
    """Identidade configurada do executor de decisões, usada em cache e auditoria.

    ``mode`` distingue ``traditional_llm``, ``jev`` e executores de teste (``fake``).
    O modelo efetivo de cada tentativa é registrado separadamente pela telemetria.
    """

    provider: str
    model: str
    mode: str


class DecisionModelPort(ABC):
    """Porta agnóstica para motores de julgamento JEV."""

    def model_identity(self) -> ModelIdentity:
        """Identidade configurada; adaptadores devem sobrescrever com valores reais."""
        return ModelIdentity(provider=type(self).__name__, model="unknown", mode="unknown")

    def component_versions(self, pack_id: str, context: dict[str, Any]) -> dict[str, str]:
        """Versões de prompt/parser/orientação aplicadas pelo adaptador, sem segredos."""
        del pack_id, context
        return {}

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
