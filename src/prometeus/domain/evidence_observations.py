"""Modelos canônicos de observação de evidências de mercado (Tarefa 1.1).

Cada campo material mantém valor, unidade, status explícito e proveniência (JSON pointer).
Preserva bruto imutável e transformações versionadas sem inferências arbitrárias.
"""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ObservationStatus(StrEnum):
    """Estados estritos de observação sem equivalência mútua."""

    OBSERVED = "observed"
    OBSERVED_ZERO = "observed_zero"
    MISSING = "missing"
    UNSUPPORTED = "unsupported"
    AMBIGUOUS = "ambiguous"
    PARTIAL = "partial"
    CENSORED = "censored"
    FAILED = "failed"


class ObservationField(BaseModel, Generic[T]):
    """Campo de dado com proveniência e estado probatório explícito."""

    value: T | None = None
    status: ObservationStatus = ObservationStatus.MISSING
    unit: str | None = None
    pointer: str | None = None
    observed_at: str | None = None

    @classmethod
    def observed(
        cls, value: T, *, pointer: str | None = None, unit: str | None = None, observed_at: str | None = None
    ) -> ObservationField[T]:
        return cls(
            value=value,
            status=ObservationStatus.OBSERVED,
            unit=unit,
            pointer=pointer,
            observed_at=observed_at,
        )

    @classmethod
    def observed_zero(
        cls, *, pointer: str | None = None, unit: str | None = None, observed_at: str | None = None
    ) -> ObservationField[T]:
        return cls(
            value=None,
            status=ObservationStatus.OBSERVED_ZERO,
            unit=unit,
            pointer=pointer,
            observed_at=observed_at,
        )

    @classmethod
    def missing(cls, *, pointer: str | None = None, unit: str | None = None) -> ObservationField[T]:
        return cls(value=None, status=ObservationStatus.MISSING, unit=unit, pointer=pointer)

    @classmethod
    def unsupported(cls, *, pointer: str | None = None) -> ObservationField[T]:
        return cls(value=None, status=ObservationStatus.UNSUPPORTED, pointer=pointer)


class BaseObservation(BaseModel):
    """Base imutável para observações de evidências de mercado."""

    source_name: str
    source_url: str
    normalizer_version: str = "obs-v1"
    raw_payload: dict[str, Any] = Field(default_factory=dict)

    def canonical_hash(self) -> str:
        data = self.model_dump(exclude={"raw_payload", "normalizer_version"}, mode="json")
        encoded = json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class PriceObservation(BaseModel):
    """Condição comercial observada de oferta educacional."""

    total_price: ObservationField[float] = Field(default_factory=ObservationField.missing)
    installments: ObservationField[int] = Field(default_factory=ObservationField.missing)
    installment_value: ObservationField[float] = Field(default_factory=ObservationField.missing)
    currency: ObservationField[str] = Field(default_factory=ObservationField.missing)
    period: ObservationField[str] = Field(default_factory=ObservationField.missing)


class OfferObservation(BaseObservation):
    """Oferta de curso educacional (concorrente direta, adjacente ou própria)."""

    title: ObservationField[str] = Field(default_factory=ObservationField.missing)
    institution_name: ObservationField[str] = Field(default_factory=ObservationField.missing)
    category: ObservationField[str] = Field(default_factory=ObservationField.missing)
    modality: ObservationField[str] = Field(default_factory=ObservationField.missing)
    workload_hours: ObservationField[int] = Field(default_factory=ObservationField.missing)
    pricing: PriceObservation | None = None
    curriculum_modules: list[str] = Field(default_factory=list)
    curriculum_text: ObservationField[str] = Field(default_factory=ObservationField.missing)


class JobObservation(BaseObservation):
    """Vaga de emprego como sinal de empregabilidade e competências."""

    title: ObservationField[str] = Field(default_factory=ObservationField.missing)
    company_name: ObservationField[str] = Field(default_factory=ObservationField.missing)
    location: ObservationField[str] = Field(default_factory=ObservationField.missing)
    country: ObservationField[str] = Field(default_factory=ObservationField.missing)
    description_text: ObservationField[str] = Field(default_factory=ObservationField.missing)
    responsibilities: list[str] = Field(default_factory=list)
    requirements_skills: list[str] = Field(default_factory=list)
    salary_text: ObservationField[str] = Field(default_factory=ObservationField.missing)
    employment_type: ObservationField[str] = Field(default_factory=ObservationField.missing)


class TrendSeriesPoint(BaseModel):
    """Ponto temporal de série quantitativa de interesse de busca."""

    time: str
    formatted_time: str | None = None
    value: list[int | float] = Field(default_factory=list)
    is_partial: bool = False
    has_data: bool | None = None


class TrendSeries(BaseObservation):
    """Série temporal de volume e interesse relativo."""

    term: str
    points: list[TrendSeriesPoint] = Field(default_factory=list)
    total_points: int = 0
    valid_points: int = 0
    positive_points: int = 0
    partial_points: int = 0
    average_interest: float = 0.0
    growth_trend_pct: float = 0.0


class AdObservation(BaseObservation):
    """Anúncio pago observado em biblioteca de anúncios."""

    ad_id: str
    page_name: ObservationField[str] = Field(default_factory=ObservationField.missing)
    headline: ObservationField[str] = Field(default_factory=ObservationField.missing)
    ad_text: ObservationField[str] = Field(default_factory=ObservationField.missing)
    cta_url: ObservationField[str] = Field(default_factory=ObservationField.missing)
    is_own_institution: bool = False


class SocialObservation(BaseObservation):
    """Manifestação espontânea em canais sociais (comentário, post)."""

    channel: str
    post_id: str
    author: ObservationField[str] = Field(default_factory=ObservationField.missing)
    text: ObservationField[str] = Field(default_factory=ObservationField.missing)
    published_at: ObservationField[str] = Field(default_factory=ObservationField.missing)
    sentiment_hint: str | None = None


class PageAcquisition(BaseObservation):
    """Página ou arquivo adquirido com registro técnico de outcome."""

    status_code: int | None = None
    outcome: str = "fetched"
    mime_type: str | None = None
    title: str | None = None
    text_content: str | None = None


class EvidencePurpose(StrEnum):
    """Finalidades canônicas de uso de evidência de mercado (Tarefa 3.2)."""

    DISCOVERY = "discovery"
    PRICING = "pricing"
    DIRECT_COMPETITION = "direct_competition"
    ADJACENT_COMPETITION = "adjacent_competition"
    WORKFORCE_COMPETENCIES = "workforce_competencies"
    EMPLOYABILITY_SIGNAL = "employability_signal"
    LEARNER_DEMAND = "learner_demand"
    OWN_CONTEXT = "own_context"
    INDUSTRY_CONTEXT = "industry_context"


class EvidenceUseAssessment(BaseModel):
    """Avaliação de utilidade de uma evidência para uma finalidade específica."""

    purpose: EvidencePurpose
    usable: bool
    confidence: float = 1.0
    observable_factors: list[str] = Field(default_factory=list)
    quote_snippets: list[str] = Field(default_factory=list)
    reason: str = ""
    rejection_cause: str | None = None
    next_step: str | None = None


class MultiPurposeAssessment(BaseModel):
    """Curadoria multidimensional por finalidade para uma evidência observada."""

    assessments: dict[str, EvidenceUseAssessment] = Field(default_factory=dict)

    def is_usable_for(self, purpose: EvidencePurpose | str) -> bool:
        key = purpose.value if isinstance(purpose, EvidencePurpose) else str(purpose)
        assessment = self.assessments.get(key)
        return bool(assessment and assessment.usable)

    @property
    def usable_purposes(self) -> list[str]:
        return [p for p, a in self.assessments.items() if a.usable]


