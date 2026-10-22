"""Módulo de backup, integridade SHA-256 e restauração atômica do banco PostgreSQL."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from prometeus.infrastructure.db.models import (
    AnalysisModel,
    AnalysisStepModel,
    AuditEventModel,
    ConfigSnapshotModel,
    CourseOutcomeModel,
    DossierModel,
    HistoricalCourseModel,
    HistoricalFunnelModel,
    HumanDecisionModel,
    WebhookDeliveryModel,
)

logger = logging.getLogger("prometeus.operations.backup")

TABLE_MODELS = [
    ("analyses", AnalysisModel),
    ("analysis_steps", AnalysisStepModel),
    ("audit_events", AuditEventModel),
    ("config_snapshots", ConfigSnapshotModel),
    ("historical_courses", HistoricalCourseModel),
    ("historical_funnel_records", HistoricalFunnelModel),
    ("dossiers", DossierModel),
    ("human_decisions", HumanDecisionModel),
    ("course_outcomes", CourseOutcomeModel),
    ("webhook_deliveries", WebhookDeliveryModel),
]


def serialize_value(val: Any) -> Any:
    """Converte valores complexos (datetime, etc.) para JSON serializável."""
    if isinstance(val, datetime):
        return val.isoformat()
    return val


def deserialize_value(val: Any, col_name: str, col_type: Any) -> Any:
    """Converte strings de volta para datetime quando necessário."""
    if isinstance(val, str) and (
        "time" in col_type.__class__.__name__.lower() or col_name.endswith(("_at", "_timestamp"))
    ):
        try:
            return datetime.fromisoformat(val)
        except ValueError:
            return val
    return val


@dataclass
class BackupManifest:
    version: int
    product: str
    created_at: str
    total_records: int
    table_counts: dict[str, int]
    payload_sha256: str


class BackupRestoreManager:
    """Gerenciador de backup e recuperação com verificação estrita de integridade."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_backup(self, output_path: Path | str) -> BackupManifest:
        """Extrai todos os dados relacionais e grava arquivo assinado com checksum SHA-256."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload: dict[str, list[dict[str, Any]]] = {}
        table_counts: dict[str, int] = {}
        total_records = 0

        for table_name, model_cls in TABLE_MODELS:
            stmt = select(model_cls)
            result = await self.session.execute(stmt)
            rows = result.scalars().all()

            records: list[dict[str, Any]] = []
            for row in rows:
                record: dict[str, Any] = {}
                for col in model_cls.__table__.columns:
                    val = getattr(row, col.name)
                    record[col.name] = serialize_value(val)
                records.append(record)

            payload[table_name] = records
            table_counts[table_name] = len(records)
            total_records += len(records)

        payload_bytes = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        payload_sha256 = hashlib.sha256(payload_bytes).hexdigest()

        manifest = BackupManifest(
            version=1,
            product="Prometeus",
            created_at=datetime.now(UTC).isoformat(),
            total_records=total_records,
            table_counts=table_counts,
            payload_sha256=payload_sha256,
        )

        backup_data = {
            "manifest": asdict(manifest),
            "payload": payload,
        }

        with path.open("w", encoding="utf-8") as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)

        logger.info(
            f"Backup gerado com sucesso em {path} ({total_records} registros, sha256={payload_sha256[:12]}...)"
        )
        return manifest

    @staticmethod
    def verify_integrity(backup_path: Path | str) -> bool:
        """Valida que o arquivo não sofreu corrupção ou adulteração conferindo o hash SHA-256."""
        path = Path(backup_path)
        if not path.exists():
            raise FileNotFoundError(f"Arquivo de backup não encontrado: {path}")

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        manifest = data.get("manifest", {})
        payload = data.get("payload", {})
        expected_sha = manifest.get("payload_sha256", "")

        computed_sha = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()

        is_valid = computed_sha == expected_sha
        if not is_valid:
            logger.error(
                f"Falha de integridade no backup {path}! Esperado={expected_sha}, Calculado={computed_sha}"
            )
        return bool(is_valid)

    async def restore_backup(
        self, backup_path: Path | str, clean_existing: bool = True
    ) -> dict[str, Any]:
        """Restaura todos os registros do arquivo de backup de forma transacional e atômica."""
        path = Path(backup_path)
        if not self.verify_integrity(path):
            raise ValueError(
                f"Abortando restauração: Checksum SHA-256 do arquivo {path} é inválido ou corrompido!"
            )

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        payload = data["payload"]
        restored_counts: dict[str, int] = {}

        try:
            if clean_existing:
                for _, model_cls in reversed(TABLE_MODELS):
                    await self.session.execute(delete(model_cls))
                await self.session.flush()

            for table_name, model_cls in TABLE_MODELS:
                records = payload.get(table_name, [])
                for item in records:
                    kwargs: dict[str, Any] = {}
                    for col in model_cls.__table__.columns:
                        if col.name in item:
                            kwargs[col.name] = deserialize_value(item[col.name], col.name, col.type)
                    instance = model_cls(**kwargs)
                    self.session.add(instance)
                await self.session.flush()
                restored_counts[table_name] = len(records)

            await self.session.commit()
            logger.info(f"Restauração do backup {path} concluída com sucesso!")
            return {
                "status": "RESTORED",
                "backup_path": str(path),
                "restored_counts": restored_counts,
                "total_restored": sum(restored_counts.values()),
            }
        except Exception as exc:
            await self.session.rollback()
            logger.error(f"Erro durante a restauração do backup {path}: {exc}. Rollback executado.")
            raise
