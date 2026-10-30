"""Modelos de domínio canônicos para o dossiê executivo e síntese generativa (Fase 06)."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

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

    PENDING = "pending"
    VERIFIED = "verified"
    UNSUPPORTED = "unsupported"
    FLAGGED_HALLUCINATION = "flagged_hallucination"
    REJECTED = "rejected"


class DossierStatus(StrEnum):
    """Estado de conformidade do dossiê."""

    DRAFT = "DRAFT"
    VERIFIED = "VERIFIED"
    REVISION_REQUIRED = "REVISION_REQUIRED"


class ReviewStatus(StrEnum):
    """Status de conformidade de cada uma das três frentes de revisão especializada."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True)
class DossierFactItem:
    """Item factual aprovado e auditado para consumo da LLM generativa."""

    evidence_id: str
    source_type: str  # "market_evidence", "jev_decision", "scoring_result", "institutional_history"
    title: str
    key_metrics: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    source_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_type": self.source_type,
            "title": self.title,
            "key_metrics": self.key_metrics,
            "summary": self.summary,
            "source_url": self.source_url,
        }


@dataclass
class IntegrityReport:
    """Relatório de integridade comparando source -> observation -> brief (Fase 1 — Tarefa 1.3)."""

    source_count: int = 0
    observations_count: int = 0
    brief_facts_count: int = 0
    job_descriptions_expected: int = 0
    job_descriptions_available: int = 0
    missing_descriptions_count: int = 0
    omissions: list[dict[str, Any]] = field(default_factory=list)
    status: str = "INTACT"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_count": self.source_count,
            "observations_count": self.observations_count,
            "brief_facts_count": self.brief_facts_count,
            "job_descriptions_expected": self.job_descriptions_expected,
            "job_descriptions_available": self.job_descriptions_available,
            "missing_descriptions_count": self.missing_descriptions_count,
            "omissions": self.omissions,
            "status": self.status,
        }


class DataIntegrityReview(BaseModel):
    """Revisão 1: Integridade dos dados (source -> observation -> brief).

    Verifica se o conteúdo essencial foi preservado sem perdas determinísticas silenciosas.
    """

    status: ReviewStatus = ReviewStatus.PASS
    source_count: int = 0
    observations_count: int = 0
    brief_facts_count: int = 0
    missing_descriptions_count: int = 0
    omissions: list[dict[str, Any]] = Field(default_factory=list)
    issues: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class SeniorAnalyticalReview(BaseModel):
    """Revisão 2: Qualidade analítica sênior.

    Verifica adequação à pergunta, independência, materialidade, alternativas, proxies e contraprovas.
    """

    status: ReviewStatus = ReviewStatus.PASS
    question_coverage: dict[str, bool] = Field(default_factory=dict)
    independence_verified: bool = True
    material_alternatives_present: bool = True
    counterevidence_analyzed: bool = True
    proxies_properly_qualified: bool = True
    issues: list[dict[str, Any]] = Field(default_factory=list)
    actionable_recommendations: list[str] = Field(default_factory=list)


class FactualDraftingReview(BaseModel):
    """Revisão 3: Factualidade da redação.

    Verifica números, unidades, identidades, claims e ausência de alucinações e prompt injection.
    """

    status: ReviewStatus = ReviewStatus.PASS
    numeric_consistency: bool = True
    identity_consistency: bool = True
    no_hallucinations: bool = True
    no_injection: bool = True
    unsupported_claims_count: int = 0
    hallucinations_count: int = 0
    issues: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ThreeFoldDossierReview(BaseModel):
    """Consolidação das três revisões especializadas com diagnósticos acionáveis."""

    data_integrity: DataIntegrityReview = Field(default_factory=DataIntegrityReview)
    senior_analytical: SeniorAnalyticalReview = Field(default_factory=SeniorAnalyticalReview)
    factual_drafting: FactualDraftingReview = Field(default_factory=FactualDraftingReview)
    overall_status: DossierStatus = DossierStatus.VERIFIED
    summary: str = ""
    actionable_feedback: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


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
    pillar_details: dict[str, Any] = field(default_factory=dict)
    scoring_experimental: bool = True
    items: list[DossierFactItem] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    course_understanding: dict[str, Any] = field(default_factory=dict)
    research_plan: dict[str, Any] = field(default_factory=dict)
    counterevidence: list[str] = field(default_factory=list)
    analysis_audit: dict[str, Any] = field(default_factory=dict)

    def compute_facts_hash(self) -> str:
        """Gera hash SHA-256 canônico e imutável para proveniência do dossiê."""
        payload = {
            "analysis_id": self.analysis_id,
            "course_name": self.course_name,
            "target_audience": self.target_audience,
            "recommendation": self.recommendation,
            "viability_score": round(self.viability_score, 2),
            "coverage_score": round(self.coverage_score, 4),
            "confidence_score": round(self.confidence_score, 4),
            "pillar_summaries": {k: round(v, 2) for k, v in sorted(self.pillar_summaries.items())},
            "pillar_details": self.pillar_details,
            "scoring_experimental": self.scoring_experimental,
            "citable_contract_version": 3,
            "items": [item.to_dict() for item in sorted(self.citable_items(), key=lambda x: x.evidence_id)],
            "limitations": sorted(self.limitations),
            "course_understanding": self.course_understanding,
            "research_plan": self.research_plan,
            "counterevidence": sorted(self.counterevidence),
            "analysis_audit": self.analysis_audit,
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get_fact_item(self, evidence_id: str) -> DossierFactItem | None:
        """Localiza um item factual por ID."""
        if evidence_id == "scoring_result":
            return DossierFactItem(
                evidence_id="scoring_result",
                source_type="computed_scoring",
                title="Resultado consolidado calculado e definições metodológicas",
                key_metrics={
                    "recommendation": self.recommendation,
                    "viability_score": self.viability_score,
                    "coverage_score": self.coverage_score,
                    "coverage_percent": round(self.coverage_score * 100, 2),
                    "confidence_score": self.confidence_score,
                    "confidence_percent": round(self.confidence_score * 100, 2),
                    "scoring_experimental": self.scoring_experimental,
                    "pillar_scores": self.pillar_summaries,
                    "pillar_details": self.pillar_details,
                },
                summary=(
                    "Resultado calculado em código, não aprovação institucional. "
                    "INSUFFICIENT_EVIDENCE significa evidências insuficientes para recomendar lançamento. "
                    "O índice de viabilidade usa escala de zero a cem; não é probabilidade de sucesso "
                    "nem projeção ou garantia de retorno financeiro. "
                    "Cobertura de evidências é a soma ponderada das dimensões com dados, "
                    "não a parcela do mercado pesquisado. "
                    "Confiança analítica mede a qualidade do suporte da análise, não a probabilidade "
                    "de sucesso do curso. "
                    + (
                        "O índice é experimental e sujeito a calibração. "
                        if self.scoring_experimental
                        else ""
                    )
                    + "Limitações: "
                    + " | ".join(dict.fromkeys(self.limitations))
                ),
            )
        for item in self.items:
            if item.evidence_id == evidence_id:
                return item
        return None

    def citable_items(self) -> list[DossierFactItem]:
        """A mesma fonte canônica chega ao redator e aos dois verificadores."""
        scoring = self.get_fact_item("scoring_result")
        assert scoring is not None
        return [scoring, *[item for item in self.items if item.evidence_id != "scoring_result"]]

    def get_all_known_ids(self) -> set[str]:
        """Conjunto completo de IDs de evidência e referências canônicas válidas."""
        known = {item.evidence_id for item in self.items}
        known.add("scoring_result")
        return known


class DossierClaim(BaseModel):
    """Afirmação individual gerada pela LLM vinculada a evidências de suporte."""

    claim_id: str = Field(default_factory=lambda: f"CLM-{uuid.uuid4().hex[:8].upper()}")
    statement: str
    claim_type: ClaimType = ClaimType.QUALITATIVE
    evidence_ids: list[str] = Field(default_factory=list)
    support_level: SupportLevel = SupportLevel.OBSERVED
    verification_status: VerificationStatus = VerificationStatus.PENDING
    verification_note: str | None = None


class DossierSection(BaseModel):
    """Seção temática do dossiê voltada a um público decisor específico."""

    section_id: str
    title: str
    target_audience: str  # "executive" | "academic" | "marketing"
    content: str
    claim_ids: list[str] = Field(default_factory=list)


class DossierValidationCriterion(BaseModel):
    model_config = {"extra": "forbid"}
    criterion: str
    target: str
    claim_ids: list[str] = Field(min_length=1)
    status: Literal["pending"] = "pending"


class DossierAction(BaseModel):
    model_config = {"extra": "forbid"}
    area: str
    action: str
    claim_ids: list[str] = Field(min_length=1)
    priority: Literal["high", "medium", "low"] = "medium"
    status: Literal["proposed"] = "proposed"


class DossierComparison(BaseModel):
    model_config = {"extra": "forbid"}
    label: str = Field(min_length=1)
    claim_ids: list[str] = Field(min_length=1)


class DossierCurriculumAlignment(BaseModel):
    model_config = {"extra": "forbid"}
    module: str = Field(min_length=1)
    need_claim_ids: list[str] = Field(min_length=1)
    coverage_claim_ids: list[str] = Field(min_length=1)


class DossierHighlights(BaseModel):
    """Destaques referenciam claims verificáveis; não concedem aprovações institucionais."""

    model_config = {"extra": "forbid"}
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    validation_criteria: list[DossierValidationCriterion] = Field(default_factory=list)
    action_recommendations: list[DossierAction] = Field(default_factory=list)
    competitors: list[DossierComparison] = Field(default_factory=list)
    curriculum_alignment: list[DossierCurriculumAlignment] = Field(default_factory=list)


class DossierOutput(BaseModel):
    """Dossiê estruturado completo, verificado e persistível."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    analysis_id: str
    prompt_version: str = "dossier-v1"
    model_name: str = "gpt-4o-mini"
    executive_summary: str
    schema_version: Literal[1, 2, 3] = 1
    executive_summary_claim_ids: list[str] = Field(default_factory=list)
    highlights: DossierHighlights = Field(default_factory=DossierHighlights)
    sections: list[DossierSection] = Field(default_factory=list)
    claims: list[DossierClaim] = Field(default_factory=list)
    facts_hash: str
    status: DossierStatus = DossierStatus.DRAFT
    verification_issues: list[dict[str, Any]] = Field(default_factory=list)
    three_fold_review: ThreeFoldDossierReview | None = None
    cost_usd: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def get_claim(self, claim_id: str) -> DossierClaim | None:
        for claim in self.claims:
            if claim.claim_id == claim_id:
                return claim
        return None

    def referenced_blocks(self) -> list[tuple[str, list[str]]]:
        """Todo texto visível e suas claims, compartilhado pelos gates numérico e semântico."""
        refs = self.executive_summary_claim_ids or [claim.claim_id for claim in self.claims]
        blocks = [(self.executive_summary, refs)]
        blocks.extend(
            (section.title + "\n" + section.content, section.claim_ids) for section in self.sections
        )
        blocks.extend(
            (item.criterion + "\n" + item.target, item.claim_ids)
            for item in self.highlights.validation_criteria
        )
        blocks.extend(
            (item.area + "\n" + item.action, item.claim_ids)
            for item in self.highlights.action_recommendations
        )
        blocks.extend((item.label, item.claim_ids) for item in self.highlights.competitors)
        blocks.extend(
            (item.module, [*item.need_claim_ids, *item.coverage_claim_ids])
            for item in self.highlights.curriculum_alignment
        )
        return blocks
