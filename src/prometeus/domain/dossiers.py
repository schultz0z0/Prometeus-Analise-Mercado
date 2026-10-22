"""Modelos de domínio canônicos para o dossiê executivo e síntese generativa (Fase 06)."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ClaimType(StrEnum):
    """Tipo da afirmação contida no dossiê."""

    QUANTITATIVE = "quantitative"
    QUALITATIVE = "qualitative"
    STRATEGIC = "strategic"


class SupportLevel(StrEnum):
    """Nível de sustentação factual da afirmação."""

    OBSERVED = "observed"  # Diretamente comprovado por evidências ou métricas coletadas
    SUGGESTIVE = "suggestive"  # Tendência inferida a partir de correlações e histórico
    HYPOTHESIS = "hypothesis"  # Proposta estratégica ou recomendação a validar


class VerificationStatus(StrEnum):
    """Resultado da verificação determinística de suporte da claim."""

    VERIFIED = "verified"
    UNSUPPORTED = "unsupported"
    FLAGGED_HALLUCINATION = "flagged_hallucination"
    REJECTED = "rejected"


class DossierStatus(StrEnum):
    """Estado de conformidade do dossiê."""

    DRAFT = "DRAFT"
    VERIFIED = "VERIFIED"
    REVISION_REQUIRED = "REVISION_REQUIRED"


@dataclass(frozen=True)
class DossierFactItem:
    """Item factual aprovado e auditado para consumo da LLM generativa."""

    evidence_id: str
    source_type: str  # "market_evidence", "jev_decision", "scoring_result", "institutional_history"
    title: str
    key_metrics: dict[str, Any] = field(default_factory=dict)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_type": self.source_type,
            "title": self.title,
            "key_metrics": self.key_metrics,
            "summary": self.summary,
        }


@dataclass
class DossierFacts:
    """Conjunto de fatos consolidados e auditados para geração do dossiê."""

    analysis_id: str
    course_name: str
    target_audience: str
    recommendation: str
    viability_score: float
    coverage_score: float
    confidence_score: float
    pillar_summaries: dict[str, float] = field(default_factory=dict)
    items: list[DossierFactItem] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def compute_facts_hash(self) -> str:
        """Gera hash SHA-256 canônico e imutável para proveniência do dossiê."""
        payload = {
            "analysis_id": self.analysis_id,
            "course_name": self.course_name,
            "recommendation": self.recommendation,
            "viability_score": round(self.viability_score, 2),
            "coverage_score": round(self.coverage_score, 4),
            "confidence_score": round(self.confidence_score, 4),
            "pillar_summaries": {k: round(v, 2) for k, v in sorted(self.pillar_summaries.items())},
            "items": [item.to_dict() for item in sorted(self.items, key=lambda x: x.evidence_id)],
            "limitations": sorted(self.limitations),
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get_fact_item(self, evidence_id: str) -> DossierFactItem | None:
        """Localiza um item factual por ID."""
        for item in self.items:
            if item.evidence_id == evidence_id:
                return item
        return None

    def get_all_known_ids(self) -> set[str]:
        """Conjunto completo de IDs de evidência e referências canônicas válidas."""
        known = {item.evidence_id for item in self.items}
        known.add("scoring_result")
        known.add("institutional_history")
        return known


class DossierClaim(BaseModel):
    """Afirmação individual gerada pela LLM vinculada a evidências de suporte."""

    claim_id: str = Field(default_factory=lambda: f"CLM-{uuid.uuid4().hex[:8].upper()}")
    statement: str
    claim_type: ClaimType = ClaimType.QUALITATIVE
    evidence_ids: list[str] = Field(default_factory=list)
    support_level: SupportLevel = SupportLevel.OBSERVED
    verification_status: VerificationStatus = VerificationStatus.VERIFIED
    verification_note: str | None = None


class DossierSection(BaseModel):
    """Seção temática do dossiê voltada a um público decisor específico."""

    section_id: str
    title: str
    target_audience: str  # "executive" | "academic" | "marketing"
    content: str
    claim_ids: list[str] = Field(default_factory=list)


class DossierOutput(BaseModel):
    """Dossiê estruturado completo, verificado e persistível."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    analysis_id: str
    prompt_version: str = "dossier-v1"
    model_name: str = "gpt-4o-mini"
    executive_summary: str
    sections: list[DossierSection] = Field(default_factory=list)
    claims: list[DossierClaim] = Field(default_factory=list)
    facts_hash: str
    status: DossierStatus = DossierStatus.VERIFIED
    cost_usd: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def get_claim(self, claim_id: str) -> DossierClaim | None:
        for claim in self.claims:
            if claim.claim_id == claim_id:
                return claim
        return None
