"""Repositório assíncrono para persistência de análises e auditoria em PostgreSQL."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from prometeus.domain.analyses import (
    Analysis,
    AnalysisRecommendation,
    AnalysisStatus,
    AnalysisStep,
    AuditEvent,
)
from prometeus.infrastructure.db.models import (
    AnalysisModel,
    AnalysisStepModel,
    AuditEventModel,
    ConfigSnapshotModel,
)


class AnalysisRepository:
    """Repositório de persistência para a raiz de agregação Analysis."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, analysis: Analysis) -> None:
        """Salva ou atualiza a análise e sincroniza novos eventos de auditoria e steps."""
        stmt = select(AnalysisModel).where(AnalysisModel.id == analysis.id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            model = AnalysisModel(
                id=analysis.id,
                tenant_id=analysis.tenant_id,
                course_name=analysis.course_name,
                status=analysis.status.value,
                recommendation=analysis.recommendation.value if analysis.recommendation else None,
                proposal_data=analysis.proposal_data,
                created_at=analysis.created_at,
                updated_at=analysis.updated_at,
            )
            self.session.add(model)

            for event in analysis.audit_events:
                event_model = AuditEventModel(
                    id=event.id,
                    analysis_id=analysis.id,
                    from_status=event.from_status.value if event.from_status else None,
                    to_status=event.to_status.value,
                    reason=event.reason,
                    correlation_id=event.correlation_id,
                    created_at=event.created_at,
                )
                self.session.add(event_model)

            for step in analysis.steps:
                step_model = AnalysisStepModel(
                    id=step.id,
                    analysis_id=analysis.id,
                    step_number=step.step_number,
                    name=step.name,
                    status=step.status,
                    started_at=step.started_at,
                    finished_at=step.finished_at,
                    output_summary=step.output_summary,
                    error_message=step.error_message,
                )
                self.session.add(step_model)

            await self.session.flush()
            return

        # Atualiza campos escalares da análise existente
        model.status = analysis.status.value
        model.recommendation = analysis.recommendation.value if analysis.recommendation else None
        model.proposal_data = analysis.proposal_data
        model.updated_at = analysis.updated_at

        # Busca IDs já persistidos para evitar re-inserção ou lazy-load acidental
        event_ids_stmt = select(AuditEventModel.id).where(
            AuditEventModel.analysis_id == analysis.id
        )
        existing_event_ids = set((await self.session.execute(event_ids_stmt)).scalars().all())

        for event in analysis.audit_events:
            if event.id not in existing_event_ids:
                event_model = AuditEventModel(
                    id=event.id,
                    analysis_id=analysis.id,
                    from_status=event.from_status.value if event.from_status else None,
                    to_status=event.to_status.value,
                    reason=event.reason,
                    correlation_id=event.correlation_id,
                    created_at=event.created_at,
                )
                self.session.add(event_model)

        step_ids_stmt = select(AnalysisStepModel).where(
            AnalysisStepModel.analysis_id == analysis.id
        )
        existing_steps = {
            s.id: s for s in (await self.session.execute(step_ids_stmt)).scalars().all()
        }

        for step in analysis.steps:
            if step.id not in existing_steps:
                step_model = AnalysisStepModel(
                    id=step.id,
                    analysis_id=analysis.id,
                    step_number=step.step_number,
                    name=step.name,
                    status=step.status,
                    started_at=step.started_at,
                    finished_at=step.finished_at,
                    output_summary=step.output_summary,
                    error_message=step.error_message,
                )
                self.session.add(step_model)
            else:
                sm = existing_steps[step.id]
                sm.status = step.status
                sm.started_at = step.started_at
                sm.finished_at = step.finished_at
                sm.output_summary = step.output_summary
                sm.error_message = step.error_message

        await self.session.flush()

    async def get_by_id(self, analysis_id: str) -> Analysis | None:
        """Recupera a análise por ID reconstituindo a raiz de agregação com auditoria e steps."""
        stmt = (
            select(AnalysisModel)
            .options(
                selectinload(AnalysisModel.audit_events),
                selectinload(AnalysisModel.steps),
            )
            .where(AnalysisModel.id == analysis_id)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        audit_events = [
            AuditEvent(
                id=e.id,
                analysis_id=e.analysis_id,
                from_status=AnalysisStatus(e.from_status) if e.from_status else None,
                to_status=AnalysisStatus(e.to_status),
                reason=e.reason,
                correlation_id=e.correlation_id,
                created_at=e.created_at,
            )
            for e in model.audit_events
        ]

        steps = [
            AnalysisStep(
                id=s.id,
                analysis_id=s.analysis_id,
                step_number=s.step_number,
                name=s.name,
                status=s.status,
                started_at=s.started_at,
                finished_at=s.finished_at,
                output_summary=s.output_summary,
                error_message=s.error_message,
            )
            for s in model.steps
        ]

        return Analysis(
            id=model.id,
            tenant_id=model.tenant_id,
            course_name=model.course_name,
            proposal_data=model.proposal_data,
            status=AnalysisStatus(model.status),
            recommendation=AnalysisRecommendation(model.recommendation)
            if model.recommendation
            else None,
            created_at=model.created_at,
            updated_at=model.updated_at,
            audit_events=audit_events,
            steps=steps,
        )

    async def list_by_tenant(
        self, tenant_id: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[Analysis]:
        """Lista análises ordenadas por data decrescente."""
        stmt = (
            select(AnalysisModel)
            .options(
                selectinload(AnalysisModel.audit_events),
                selectinload(AnalysisModel.steps),
            )
            .order_by(AnalysisModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if tenant_id:
            stmt = stmt.where(AnalysisModel.tenant_id == tenant_id)

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        analyses: list[Analysis] = []
        for m in models:
            rec = AnalysisRecommendation(m.recommendation) if m.recommendation else None
            analyses.append(
                Analysis(
                    id=m.id,
                    tenant_id=m.tenant_id,
                    course_name=m.course_name,
                    proposal_data=m.proposal_data,
                    status=AnalysisStatus(m.status),
                    recommendation=rec,
                    created_at=m.created_at,
                    updated_at=m.updated_at,
                    audit_events=[
                        AuditEvent(
                            id=e.id,
                            analysis_id=e.analysis_id,
                            from_status=AnalysisStatus(e.from_status) if e.from_status else None,
                            to_status=AnalysisStatus(e.to_status),
                            reason=e.reason,
                            correlation_id=e.correlation_id,
                            created_at=e.created_at,
                        )
                        for e in m.audit_events
                    ],
                    steps=[],
                )
            )
        return analyses

    async def save_config_snapshot(
        self,
        analysis_id: str,
        tenant_id: str,
        scoring_profile_id: str,
        tenant_config_snapshot: dict[str, Any],
        scoring_profile_snapshot: dict[str, Any],
    ) -> None:
        """Salva snapshot imutável de configurações associado à análise."""
        snapshot = ConfigSnapshotModel(
            id=str(uuid.uuid4()),
            analysis_id=analysis_id,
            tenant_id=tenant_id,
            scoring_profile_id=scoring_profile_id,
            tenant_config_snapshot=tenant_config_snapshot,
            scoring_profile_snapshot=scoring_profile_snapshot,
        )
        self.session.add(snapshot)
        await self.session.flush()
