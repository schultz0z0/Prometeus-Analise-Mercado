"""Modelos SQLAlchemy para persistência relacional em PostgreSQL.

Define tabelas para análises, etapas de workflow, snapshots de configuração
e eventos de auditoria imutáveis.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
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
