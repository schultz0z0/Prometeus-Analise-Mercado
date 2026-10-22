"""Modelos SQLAlchemy para persistência relacional em PostgreSQL.

Define tabelas para análises, etapas de workflow, snapshots de configuração
e eventos de auditoria imutáveis.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    """Classe base declarativa para todas as tabelas do Prometeus."""

    pass


# Tipo JSON com variante nativa JSONB quando conectado ao PostgreSQL
JsonType = JSON().with_variant(postgresql.JSONB, "postgresql")


class AnalysisModel(Base):
    """Tabela de análises de viabilidade educacional."""

    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    course_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="QUEUED")
    recommendation: Mapped[str | None] = mapped_column(String(32), nullable=True)
    proposal_data: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    previous_analysis_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relacionamentos
    audit_events: Mapped[list[AuditEventModel]] = relationship(
        "AuditEventModel",
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="AuditEventModel.created_at",
    )
    steps: Mapped[list[AnalysisStepModel]] = relationship(
        "AnalysisStepModel",
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="AnalysisStepModel.step_number",
    )
    config_snapshot: Mapped[ConfigSnapshotModel | None] = relationship(
        "ConfigSnapshotModel",
        back_populates="analysis",
        uselist=False,
        cascade="all, delete-orphan",
    )
    decision_results: Mapped[list[DecisionResultModel]] = relationship(
        "DecisionResultModel",
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="DecisionResultModel.created_at",
    )
    research_plans: Mapped[list[ResearchPlanModel]] = relationship(
        "ResearchPlanModel",
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="ResearchPlanModel.created_at",
    )
    market_evidences: Mapped[list[MarketEvidenceModel]] = relationship(
        "MarketEvidenceModel",
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="MarketEvidenceModel.collected_at",
    )
    scoring_result: Mapped[ScoringResultModel | None] = relationship(
        "ScoringResultModel",
        back_populates="analysis",
        uselist=False,
        cascade="all, delete-orphan",
    )
    dossier: Mapped[DossierModel | None] = relationship(
        "DossierModel",
        back_populates="analysis",
        uselist=False,
        cascade="all, delete-orphan",
    )
    human_decisions: Mapped[list[HumanDecisionModel]] = relationship(
        "HumanDecisionModel",
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="HumanDecisionModel.created_at",
    )
    outcomes: Mapped[list[CourseOutcomeModel]] = relationship(
        "CourseOutcomeModel",
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="CourseOutcomeModel.created_at",
    )
    webhook_deliveries: Mapped[list[WebhookDeliveryModel]] = relationship(
        "WebhookDeliveryModel",
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="WebhookDeliveryModel.created_at",
    )

    __table_args__ = (Index("ix_analyses_tenant_created", "tenant_id", "created_at"),)


class AnalysisStepModel(Base):
    """Tabela de etapas de execução e checkpoints do workflow."""

    __tablename__ = "analysis_steps"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    output_summary: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    analysis: Mapped[AnalysisModel] = relationship("AnalysisModel", back_populates="steps")

    __table_args__ = (
        Index("ix_analysis_steps_analysis_step", "analysis_id", "step_number", unique=True),
    )


class AuditEventModel(Base):
    """Tabela imutável de eventos de auditoria das análises."""

    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    analysis: Mapped[AnalysisModel] = relationship("AnalysisModel", back_populates="audit_events")

    __table_args__ = (Index("ix_audit_events_analysis_created", "analysis_id", "created_at"),)


class ConfigSnapshotModel(Base):
    """Snapshot imutável das configurações vigentes no momento de criação da análise."""

    __tablename__ = "config_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    scoring_profile_id: Mapped[str] = mapped_column(String(64), nullable=False)
    tenant_config_snapshot: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    scoring_profile_snapshot: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    analysis: Mapped[AnalysisModel] = relationship(
        "AnalysisModel", back_populates="config_snapshot"
    )


class HistoricalCourseModel(Base):
    """Tabela de cursos históricos persistidos por instituição (PostgreSQL)."""

    __tablename__ = "historical_courses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    modality: Mapped[str] = mapped_column(String(64), nullable=False, default="online")
    workload_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    tags: Mapped[list[str]] = mapped_column(JsonType, nullable=False, default=list)
    target_audience: Mapped[list[str]] = mapped_column(JsonType, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    funnel_records: Mapped[list[HistoricalFunnelModel]] = relationship(
        "HistoricalFunnelModel",
        back_populates="course",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_historical_courses_tenant_ext", "tenant_id", "external_id", unique=True),
    )


class HistoricalFunnelModel(Base):
    """Tabela de métricas históricas de funil agregadas por curso e período."""

    __tablename__ = "historical_funnel_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    course_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("historical_courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_course_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    leads: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    applicants: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enrolled: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conversion_lead_to_applicant: Mapped[float] = mapped_column(nullable=False, default=0.0)
    conversion_applicant_to_enrolled: Mapped[float] = mapped_column(nullable=False, default=0.0)
    conversion_lead_to_enrolled: Mapped[float] = mapped_column(nullable=False, default=0.0)
    average_ticket_brl: Mapped[float | None] = mapped_column(nullable=True)
    total_revenue_brl: Mapped[float | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    course: Mapped[HistoricalCourseModel] = relationship(
        "HistoricalCourseModel", back_populates="funnel_records"
    )

    __table_args__ = (
        Index("ix_historical_funnel_ext_period", "external_course_id", "period", unique=True),
    )


class DecisionResultModel(Base):
    """Tabela de resultados de julgamento do JEV (PostgreSQL)."""

    __tablename__ = "decision_results"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pack_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    decision_type: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    is_noul: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    selected_choice: Mapped[str | None] = mapped_column(String(128), nullable=True)
    distribution: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    score_value: Mapped[float | None] = mapped_column(nullable=True)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JsonType, nullable=False, default=list)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False, default="jev-pinned")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    analysis: Mapped[AnalysisModel] = relationship(
        "AnalysisModel", back_populates="decision_results"
    )

    __table_args__ = (Index("ix_decision_results_analysis_pack", "analysis_id", "pack_id"),)


class ResearchPlanModel(Base):
    """Tabela de planos de pesquisa e governança de orçamento externo."""

    __tablename__ = "research_plans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    cache_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    enabled_sources: Mapped[list[str]] = mapped_column(JsonType, nullable=False, default=list)
    budget_limit_usd: Mapped[float] = mapped_column(nullable=False, default=2.0)
    spent_usd: Mapped[float] = mapped_column(nullable=False, default=0.0)
    allocated_budget: Mapped[dict[str, float]] = mapped_column(
        JsonType, nullable=False, default=dict
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PLANNED")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    analysis: Mapped[AnalysisModel] = relationship("AnalysisModel", back_populates="research_plans")

    __table_args__ = (Index("ix_research_plans_analysis_cache", "analysis_id", "cache_key"),)


class MarketEvidenceModel(Base):
    """Tabela de evidências de mercado coletadas e higienizadas (PostgreSQL)."""

    __tablename__ = "market_evidences"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidence_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    collector: Mapped[str] = mapped_column(String(64), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    sanitized_data: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    quality_score: Mapped[float] = mapped_column(nullable=False, default=1.0)
    cost_usd: Mapped[float] = mapped_column(nullable=False, default=0.0)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    analysis: Mapped[AnalysisModel] = relationship(
        "AnalysisModel", back_populates="market_evidences"
    )

    __table_args__ = (
        Index("ix_market_evidences_analysis_type", "analysis_id", "evidence_type"),
        Index("ix_market_evidences_analysis_hash", "analysis_id", "content_hash"),
    )


class ScoringResultModel(Base):
    """Tabela de pontuação, índices de viabilidade e recomendações determinísticas."""

    __tablename__ = "scoring_results"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    profile_id: Mapped[str] = mapped_column(String(64), nullable=False)
    viability_score: Mapped[float] = mapped_column(nullable=False)
    coverage_score: Mapped[float] = mapped_column(nullable=False)
    confidence_score: Mapped[float] = mapped_column(nullable=False)
    partial_score: Mapped[float] = mapped_column(nullable=False)
    recommendation: Mapped[str] = mapped_column(String(32), nullable=False)
    is_experimental: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    pillar_scores: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    gate_details: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    analysis: Mapped[AnalysisModel] = relationship("AnalysisModel", back_populates="scoring_result")

    __table_args__ = (UniqueConstraint("analysis_id", name="uq_scoring_results_analysis_id"),)


class DossierModel(Base):
    """Tabela de dossiês executivos e acadêmicos gerados e verificados (PostgreSQL)."""

    __tablename__ = "dossiers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    facts_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    sections: Mapped[list[dict[str, Any]]] = mapped_column(JsonType, nullable=False, default=list)
    claims: Mapped[list[dict[str, Any]]] = mapped_column(JsonType, nullable=False, default=list)
    cost_usd: Mapped[float] = mapped_column(nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    analysis: Mapped[AnalysisModel] = relationship("AnalysisModel", back_populates="dossier")

    __table_args__ = (UniqueConstraint("analysis_id", name="uq_dossiers_analysis_id"),)


class HumanDecisionModel(Base):
    """Tabela de decisões e feedback humano sobre a recomendação do Prometeus (RF-009)."""

    __tablename__ = "human_decisions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_role: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str] = mapped_column(String(64), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    adjustments: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    analysis: Mapped[AnalysisModel] = relationship(
        "AnalysisModel", back_populates="human_decisions"
    )


class CourseOutcomeModel(Base):
    """Tabela de desfechos reais de captação pós-lançamento (RF-013)."""

    __tablename__ = "course_outcomes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_course_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    launch_date: Mapped[str] = mapped_column(String(32), nullable=False)
    enrolled_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    leads_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    applicants_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revenue_brl: Mapped[float | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    analysis: Mapped[AnalysisModel] = relationship("AnalysisModel", back_populates="outcomes")


class WebhookDeliveryModel(Base):
    """Tabela de rastreamento de entregas de webhooks e dead-letter."""

    __tablename__ = "webhook_deliveries"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_url: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="PENDING")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    response_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    analysis: Mapped[AnalysisModel] = relationship(
        "AnalysisModel", back_populates="webhook_deliveries"
    )

    __table_args__ = (Index("ix_webhook_event_status", "event_id", "status"),)
