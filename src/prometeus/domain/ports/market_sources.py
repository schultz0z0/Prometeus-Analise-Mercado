"""Portas e modelos canônicos para coleta de dados externos de mercado.

Define tipos para trends, volume de busca, concorrência paga, ofertas educacionais,
vagas de emprego e social listening, com rastreabilidade de proveniência, quotas e custos.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EvidenceType(StrEnum):
    """Categorias canônicas de evidência externa de mercado."""

    TRENDS = "TRENDS"
    SEARCH_VOLUME = "SEARCH_VOLUME"
    PAID_COMPETITION = "PAID_COMPETITION"
    OFFER = "OFFER"
    JOB_MARKET = "JOB_MARKET"
    SOCIAL_VOICE = "SOCIAL_VOICE"


class KeywordCategory(StrEnum):
    """Classificação canônica de termos no KeywordSet."""

    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    NEGATIVE = "NEGATIVE"


class KeywordCandidate(BaseModel):
    """Candidato a termo de busca avaliado semântica e comercialmente."""

    term: str
    relevance: str = "IRRELEVANT"  # HIGH_RELEVANCE, MEDIUM_RELEVANCE, IRRELEVANT
    confidence: float = 0.0
    category: KeywordCategory = KeywordCategory.SECONDARY
    notes: str = ""


class KeywordSet(BaseModel):
    """Conjunto selecionado e governado de termos de pesquisa da análise."""

    primary_keywords: list[str] = Field(default_factory=list)
    secondary_keywords: list[str] = Field(default_factory=list)
    negative_keywords: list[str] = Field(default_factory=list)
    evaluated_candidates: list[KeywordCandidate] = Field(default_factory=list)

    @property
    def all_search_terms(self) -> list[str]:
        """Retorna termos ativos combinados (primários e secundários)."""
        return self.primary_keywords + self.secondary_keywords


class ResearchPlanStatus(StrEnum):
    """Estado do plano de pesquisa de mercado."""

    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    EXCEEDED_BUDGET = "EXCEEDED_BUDGET"
    PARTIAL = "PARTIAL"


class ResearchPlan(BaseModel):
    """Plano de pesquisa delimitado por taxonomia, features do tenant e orçamento."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    analysis_id: str
    tenant_id: str
    cache_key: str
    enabled_sources: list[str] = Field(default_factory=list)
    budget_limit_usd: float = 2.00
    spent_usd: float = 0.0
    allocated_budget: dict[str, float] = Field(default_factory=dict)
    status: ResearchPlanStatus = ResearchPlanStatus.PLANNED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def has_budget_for(self, estimated_cost_usd: float) -> bool:
        """Verifica se o custo estimado está dentro do teto orçamentário restante."""
        return (self.spent_usd + estimated_cost_usd) <= (self.budget_limit_usd + 0.001)

    def record_cost(self, cost_usd: float) -> None:
        """Registra custo incorrido e atualiza status se estourar o orçamento."""
        self.spent_usd = round(self.spent_usd + cost_usd, 4)
        if self.spent_usd > self.budget_limit_usd:
            self.status = ResearchPlanStatus.EXCEEDED_BUDGET


@dataclass(frozen=True)
class MarketEvidence:
    """Evidência de mercado imutável com proveniência e hash de integridade."""

    id: str
    analysis_id: str
    evidence_type: EvidenceType
    source_name: str
    source_url: str
    collector: str
    content_hash: str
    title: str
    raw_payload: dict[str, Any]
    sanitized_data: dict[str, Any]
    quality_score: float = 1.0
    cost_usd: float = 0.0
    collected_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls,
        analysis_id: str,
        evidence_type: EvidenceType,
        source_name: str,
        source_url: str,
        collector: str,
        title: str,
        raw_payload: dict[str, Any],
        sanitized_data: dict[str, Any] | None = None,
        quality_score: float = 1.0,
        cost_usd: float = 0.0,
        evidence_id: str | None = None,
    ) -> MarketEvidence:
        """Instancia evidência computando automaticamente o SHA-256 de integridade."""
        payload_str = json.dumps(raw_payload, sort_keys=True, ensure_ascii=False)
        content_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

        return cls(
            id=evidence_id or str(uuid.uuid4()),
            analysis_id=analysis_id,
            evidence_type=evidence_type,
            source_name=source_name,
            source_url=source_url,
            collector=collector,
            content_hash=content_hash,
            title=title,
            raw_payload=raw_payload,
            sanitized_data=sanitized_data if sanitized_data is not None else raw_payload,
            quality_score=round(quality_score, 2),
            cost_usd=round(cost_usd, 4),
        )


class MarketSourcePort(ABC):
    """Porta canônica para coletores de dados externos de mercado."""

    @abstractmethod
    async def collect(
        self,
        analysis_id: str,
        search_terms: list[str],
        plan: ResearchPlan | None = None,
    ) -> list[MarketEvidence]:
        """Executa a coleta de evidências para os termos de busca informados."""
        pass
