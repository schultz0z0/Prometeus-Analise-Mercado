"""Contratos de domínio para parecer estratégico, SWOT e TOWS (Tarefa 4.3).

Rastreia: pergunta -> achado -> evidências favoráveis/contrárias -> premissas -> materialidade -> alternativas -> lacunas.
SWOT com dimensão interna/externa, fonte/trecho, natureza epistêmica e efeito na decisão.
TOWS com matriz de estratégias (SO, WO, ST, WT) vinculadas a ações e áreas responsáveis.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class EpistemicNature(StrEnum):
    """Natureza epistêmica da afirmação estratégica."""

    OBSERVED = "observed"
    INFERRED = "inferred"
    HYPOTHESIS = "hypothesis"


class SWOTDimension(StrEnum):
    """Quatro quadrantes canônicos da análise SWOT."""

    STRENGTH = "strength"
    WEAKNESS = "weakness"
    OPPORTUNITY = "opportunity"
    THREAT = "threat"


class TOWSStrategyType(StrEnum):
    """Cruzamentos estratégicos da matriz TOWS."""

    SO = "SO"  # Forças x Oportunidades (Maxi-Maxi)
    WO = "WO"  # Fraquezas x Oportunidades (Mini-Maxi)
    ST = "ST"  # Forças x Ameaças (Maxi-Mini)
    WT = "WT"  # Fraquezas x Ameaças (Mini-Mini)


class MarketFinding(BaseModel):
    """Achado analítico de mercado estruturado com suporte probatório e contraprovas."""

    question_id: str
    question_text: str
    finding: str
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    counter_evidence_ids: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    materiality: Literal["critical", "high", "medium", "low"] = "medium"
    alternatives_considered: list[str] = Field(default_factory=list)
    remaining_gaps: list[str] = Field(default_factory=list)
    recommended_next_test: str = ""


class SWOTItem(BaseModel):
    """Item da matriz SWOT com rastreamento epistêmico e fonte."""

    id: str
    dimension: SWOTDimension
    internal_or_external: Literal["internal", "external"]
    statement: str
    evidence_source: str = ""
    quote_or_datapoint: str = ""
    epistemic_nature: EpistemicNature = EpistemicNature.OBSERVED
    temporal_validity: str = "current"
    decision_effect: str = ""


class TOWSAction(BaseModel):
    """Ação estratégica derivada da matriz TOWS."""

    id: str
    strategy_type: TOWSStrategyType
    statement: str
    action: str
    responsible_area: str
    priority: Literal["high", "medium", "low"] = "medium"


class StrategicAssessment(BaseModel):
    """Parecer estratégico abrangente com SWOT e ações TOWS."""

    analysis_id: str
    market_findings: list[MarketFinding] = Field(default_factory=list)
    swot_items: list[SWOTItem] = Field(default_factory=list)
    tows_actions: list[TOWSAction] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations_and_risks: list[str] = Field(default_factory=list)

