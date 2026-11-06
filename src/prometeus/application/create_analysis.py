"""Caso de uso de criação de análise com idempotência estrita e snapshot de governança."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from prometeus.domain.analyses import Analysis, AnalysisStatus
from prometeus.domain.configuration import (
    AppSettings,
    load_scoring_profile,
    resolve_tenant_config_for_id,
)
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import AnalysisJobModel, AnalysisModel


@dataclass
class CreateAnalysisCommand:
    """Dados de entrada para solicitação de nova análise."""

    tenant_id: str
    course_name: str
    proposal_data: dict[str, Any]
    idempotency_key: str
    correlation_id: str
    previous_analysis_id: str | None = None


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
        stmt = (
            select(AnalysisModel)
            .where(
                AnalysisModel.tenant_id == command.tenant_id,
                or_(
                    AnalysisModel.idempotency_key == command.idempotency_key,
                    and_(
                        AnalysisModel.idempotency_key.is_(None),
                        AnalysisModel.previous_analysis_id.is_(None),
                        AnalysisModel.proposal_data["_idempotency_key"].as_string()
                        == command.idempotency_key,
                    ),
                ),
            )
            .order_by(AnalysisModel.created_at, AnalysisModel.id)
            .limit(1)
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            return CreateAnalysisResult(
                analysis_id=existing.id,
                status=AnalysisStatus(existing.status),
                created_at=existing.created_at.isoformat(),
                is_existing=True,
            )

        # 2. Carrega configurações isoladas por tenant_id e do perfil de scoring para snapshot imutável
        scoring_path = Path(self.settings.SCORING_PROFILE_PATH)
        tenant_config = resolve_tenant_config_for_id(
            command.tenant_id, self.settings, allow_synthetic_fallback=True
        )
        scoring_profile = load_scoring_profile(scoring_path)

        # 3. Cria a raiz de agregação do domínio (ADR-0005: status=QUEUED, recommendation=None)
        if not command.idempotency_key.strip() or len(command.idempotency_key) > 255:
            raise ValueError("Chave de idempotência deve ter entre 1 e 255 caracteres.")
        proposal_with_idempotency = {
            key: value for key, value in command.proposal_data.items() if not key.startswith("_")
        }
        if self.settings.SHADOW_MODE:
            proposal_with_idempotency["_shadow_mode"] = True
        dumped_tenant = tenant_config.model_dump(mode="json")
        institution = dumped_tenant.get("institution", {})
        ecosystem = dumped_tenant.get("ecosystem", {})
        proposal_with_idempotency["_institution_context"] = {
            "id": command.tenant_id,
            "name": institution.get("display_name", command.tenant_id),
            "domains": institution.get("domains", []),
            "competitors": ecosystem.get("competitors", []),
            "sector_radar": ecosystem.get("sector_radar", []),
            "radar_ttl_hours": ecosystem.get("radar_ttl_hours", 168),
        }
        proposal_with_idempotency["_idempotency_key"] = command.idempotency_key

        analysis = Analysis.create(
            tenant_id=command.tenant_id,
            course_name=command.course_name,
            proposal_data=proposal_with_idempotency,
            correlation_id=command.correlation_id,
            previous_analysis_id=command.previous_analysis_id,
        )

        # 4. Persiste a análise e o snapshot de governança no banco
        connection = await self.session.connection()
        if connection.dialect.name == "sqlite":
            # sqlite3 <=3.11 não inicia uma transação para SELECT/SAVEPOINT.
            # Sem BEGIN real, RELEASE do savepoint publicaria a outbox antes do commit.
            raw = await connection.get_raw_connection()
            if raw.driver_connection is not None and not raw.driver_connection.in_transaction:
                await connection.exec_driver_sql("BEGIN")
        try:
            async with self.session.begin_nested():
                await self.repository.save(analysis)
                await self.repository.save_config_snapshot(
                    analysis_id=analysis.id,
                    tenant_id=command.tenant_id,
                    scoring_profile_id=scoring_profile.profile_id,
                    tenant_config_snapshot=dumped_tenant,
                    scoring_profile_snapshot=scoring_profile.model_dump(mode="json"),
                )
                self.session.add(
                    AnalysisJobModel(analysis_id=analysis.id, correlation_id=command.correlation_id)
                )
                await self.session.flush()
        except IntegrityError:
            # Uma criação concorrente venceu a restrição única; a transação externa continua utilizável.
            existing = (await self.session.execute(stmt)).scalar_one_or_none()
            if existing is None:
                raise
            return CreateAnalysisResult(
                existing.id, AnalysisStatus(existing.status), existing.created_at.isoformat(), True
            )

        return CreateAnalysisResult(
            analysis_id=analysis.id,
            status=analysis.status,
            created_at=analysis.created_at.isoformat(),
            is_existing=False,
        )
