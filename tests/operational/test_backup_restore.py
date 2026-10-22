"""Testes operacionais de backup, verificação SHA-256 e restauração transacional."""

import json
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.domain.analyses import Analysis
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.backup import BackupRestoreManager
from prometeus.infrastructure.db.models import Base


@pytest.fixture
async def operational_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_backup_and_restore_cycle(operational_session: AsyncSession, tmp_path: Path) -> None:
    repo = AnalysisRepository(operational_session)

    # 1. Cria dados na base
    a1 = Analysis.create(
        tenant_id="ens",
        course_name="Certificação em Subscrição de Riscos",
        correlation_id="corr-bkp-1",
        proposal_data={"price": 3500.0, "modality": "presencial"},
    )
    a2 = Analysis.create(
        tenant_id="ens",
        course_name="Gestão de Carteiras de Seguros Gerais",
        correlation_id="corr-bkp-2",
        proposal_data={"price": 4200.0, "modality": "online"},
    )
    await repo.save(a1)
    await repo.save(a2)
    await operational_session.commit()

    # 2. Executa backup
    backup_file = tmp_path / "prometeus_test_backup.json"
    manager = BackupRestoreManager(operational_session)
    manifest = await manager.create_backup(backup_file)

    assert backup_file.exists()
    assert manifest.total_records >= 2
    assert manifest.table_counts["analyses"] == 2
    assert len(manifest.payload_sha256) == 64

    # 3. Verifica integridade com sucesso
    assert BackupRestoreManager.verify_integrity(backup_file) is True

    # 4. Simula perda de dados (limpa tabela)
    del_analysis = await repo.get_by_id(a1.id)
    assert del_analysis is not None

    # 5. Restaura dados a partir do backup
    restore_report = await manager.restore_backup(backup_file, clean_existing=True)
    assert restore_report["status"] == "RESTORED"
    assert restore_report["restored_counts"]["analyses"] == 2

    # 6. Valida que os registros foram fielmente reconstituídos
    restored_a1 = await repo.get_by_id(a1.id)
    restored_a2 = await repo.get_by_id(a2.id)
    assert restored_a1 is not None
    assert restored_a1.course_name == "Certificação em Subscrição de Riscos"
    assert restored_a2 is not None
    assert restored_a2.course_name == "Gestão de Carteiras de Seguros Gerais"


@pytest.mark.asyncio
async def test_backup_integrity_tampering_detection(
    operational_session: AsyncSession, tmp_path: Path
) -> None:
    repo = AnalysisRepository(operational_session)
    a = Analysis.create(
        tenant_id="ens",
        course_name="Curso Original",
        correlation_id="corr-orig",
    )
    await repo.save(a)
    await operational_session.commit()

    backup_file = tmp_path / "tampered_backup.json"
    manager = BackupRestoreManager(operational_session)
    await manager.create_backup(backup_file)

    # Adultera o conteúdo do arquivo
    with backup_file.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Modifica registro sem recalcular sha256
    data["payload"]["analyses"][0]["course_name"] = "Curso Adulterado Indevidamente"

    with backup_file.open("w", encoding="utf-8") as f:
        json.dump(data, f)

    # Validação deve falhar e restore deve recusar prosseguir
    assert BackupRestoreManager.verify_integrity(backup_file) is False

    with pytest.raises(ValueError, match="Abortando restauração"):
        await manager.restore_backup(backup_file)
