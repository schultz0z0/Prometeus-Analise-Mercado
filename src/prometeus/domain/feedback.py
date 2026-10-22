"""Modelos de domínio para decisões humanas (RF-009) e resultados pós-lançamento (RF-013)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class HumanDecision:
    """Registro auditável de decisão humana sobre o parecer do Prometeus."""

    id: str
    analysis_id: str
    user_id: str
    user_role: str  # "director", "coordinator", "academic_lead"
    decision: str  # "APPROVED", "APPROVED_WITH_ADJUSTMENTS", "REJECTED"
    rationale: str
    adjustments: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls,
        analysis_id: str,
        user_id: str,
        user_role: str,
        decision: str,
        rationale: str,
        adjustments: dict[str, Any] | None = None,
    ) -> HumanDecision:
        return cls(
            id=f"dec_{uuid.uuid4().hex[:12]}",
            analysis_id=analysis_id,
            user_id=user_id,
            user_role=user_role,
            decision=decision,
            rationale=rationale,
            adjustments=adjustments or {},
            created_at=datetime.now(UTC),
        )


@dataclass
class CourseOutcome:
    """Registro de métricas reais de captação e matrículas pós-lançamento."""

    id: str
    analysis_id: str
    external_course_id: str
    launch_date: str
    enrolled_count: int
    leads_count: int = 0
    applicants_count: int = 0
    revenue_brl: float | None = None
    notes: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls,
        analysis_id: str,
        external_course_id: str,
        launch_date: str,
        enrolled_count: int,
        leads_count: int = 0,
        applicants_count: int = 0,
        revenue_brl: float | None = None,
        notes: str | None = None,
    ) -> CourseOutcome:
        return cls(
            id=f"out_{uuid.uuid4().hex[:12]}",
            analysis_id=analysis_id,
            external_course_id=external_course_id,
            launch_date=launch_date,
            enrolled_count=enrolled_count,
            leads_count=leads_count,
            applicants_count=applicants_count,
            revenue_brl=revenue_brl,
            notes=notes,
            created_at=datetime.now(UTC),
        )
