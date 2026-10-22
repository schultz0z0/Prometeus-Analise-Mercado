"""Caso de uso de criação de análise com idempotência estrita e snapshot de governança."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prometeus.domain.analyses import Analysis, AnalysisStatus
from prometeus.domain.configuration import (
    AppSettings,
    load_scoring_profile,
    load_tenant_config,
)
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import AnalysisModel


@dataclass
class CreateAnalysisCommand:
    """Dados de entrada para solicitação de nova análise."""

    tenant_id: str
    course_name: str
    proposal_data: dict[str, Any]
    idempotency_key: str
    correlation_id: str


@dataclass
class CreateAnalysisResult:
    """Resultado retornado pelo caso de uso."""

    analysis_id: str
    status: AnalysisStatus
    created_at: str
    is_existing: bool = False


class CreateAnalysisUseCase:
    """Orquestra a validação, snapshot, persistência e enfileiramento de uma análise."""

    def __init__(self, session: AsyncSession, settings: AppSettings | None = None) -> None:
        self.session = session
        self.repository = AnalysisRepository(session)
        self.settings = settings or AppSettings()

    async def execute(self, command: CreateAnalysisCommand) -> CreateAnalysisResult:
        # 1. Verifica idempotência: se já existe análise criada com a mesma idempotency_key
        # Procuramos no JSON proposal_data pela chave _idempotency_key
        # (funciona tanto no SQLite quanto no PostgreSQL)
        stmt = select(AnalysisModel).where(
            AnalysisModel.proposal_data["_idempotency_key"].as_string() == command.idempotency_key
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            return CreateAnalysisResult(
                analysis_id=existing.id,
                status=AnalysisStatus(existing.status),
                created_at=existing.created_at.isoformat(),
                is_existing=True,
            )

        # 2. Carrega configurações do tenant e do perfil de scoring para snapshot imutável
        tenant_path = Path(self.settings.INSTITUTION_CONFIG_PATH)
        scoring_path = Path(self.settings.SCORING_PROFILE_PATH)

        tenant_config = load_tenant_config(tenant_path)
        scoring_profile = load_scoring_profile(scoring_path)

        # 3. Cria a raiz de agregação do domínio (ADR-0005: status=QUEUED, recommendation=None)
        proposal_with_idempotency = dict(command.proposal_data)
        proposal_with_idempotency["_idempotency_key"] = command.idempotency_key

        analysis = Analysis.create(
            tenant_id=command.tenant_id,
            course_name=command.course_name,
            proposal_data=proposal_with_idempotency,
            correlation_id=command.correlation_id,
        )

        # 4. Persiste a análise e o snapshot de governança no banco
        await self.repository.save(analysis)
        await self.repository.save_config_snapshot(
            analysis_id=analysis.id,
            tenant_id=command.tenant_id,
            scoring_profile_id=scoring_profile.profile_id,
            tenant_config_snapshot=tenant_config.model_dump(),
            scoring_profile_snapshot=scoring_profile.model_dump(),
        )

        return CreateAnalysisResult(
            analysis_id=analysis.id,
            status=analysis.status,
            created_at=analysis.created_at.isoformat(),
            is_existing=False,
        )
