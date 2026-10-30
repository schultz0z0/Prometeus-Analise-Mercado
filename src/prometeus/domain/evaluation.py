"""Modelos de domínio para avaliação da inteligência de mercado e conjunto de referência humano."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class UtilityLabel(StrEnum):
    DIRECT = "direct"
    ADJACENT = "adjacent"
    CONTEXT = "context"
    IRRELEVANT = "irrelevant"
    INSUFFICIENT = "insufficient"


class EvaluationPurpose(StrEnum):
    DIRECT_COMPETITION = "direct_competition"
    ADJACENT_COMPETITION = "adjacent_competition"
    PRICING = "pricing"
    COMPETENCIES = "competencies"
    EMPLOYABILITY = "employability"
    LEARNER_DEMAND = "learner_demand"
    INSTITUTIONAL_CONTEXT = "institutional_context"
    SECTOR_CONTEXT = "sector_context"


class ControlType(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    ADJACENT = "adjacent"
    FALSE_COGNATE = "false_cognate"
    LEGITIMATE_ABSENCE = "legitimate_absence"


class AdjudicationStatus(StrEnum):
    AGREED = "AGREED"
    ADJUDICATED = "ADJUDICATED"
    UNKNOWN_UNRESOLVED = "UNKNOWN_UNRESOLVED"


class Scope(BaseModel):
    geography: str
    period: str
    language: str


class ReviewerAnnotation(BaseModel):
    reviewer_id: str
    utility: UtilityLabel
    purpose: str
    rationale: str
    timestamp: str


class Adjudication(BaseModel):
    status: AdjudicationStatus
    adjudicator: str
    final_utility: UtilityLabel
    rationale: str


class ReferenceExample(BaseModel):
    """Exemplo rotulado do conjunto de referência humano adjudicado."""

    example_id: str
    capture_id: str
    entity_id: str
    source_name: str
    source_url: str
    scope: Scope
    expected_critical_fields: list[str] = Field(default_factory=list)
    extracted_snippets: list[str] = Field(default_factory=list)
    purpose: EvaluationPurpose
    utility: UtilityLabel
    category_exact: str
    family: str
    ambiguity_flag: bool = False
    ambiguity_reason: str | None = None
    allowed_claims: list[str] = Field(default_factory=list)
    disallowed_claims: list[str] = Field(default_factory=list)
    control_type: ControlType
    annotations: list[ReviewerAnnotation]
    adjudication: Adjudication
