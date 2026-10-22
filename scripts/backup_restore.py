"""CLI operacional de backup, verificação de integridade e restauração para Prometeus."""

from __future__ import annotations

import argparse
import asyncio
import logging

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.domain.configuration import AppSettings
from prometeus.infrastructure.db.backup import BackupRestoreManager

logger = logging.getLogger("prometeus.operations.backup")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


async def run_cli() -> None:
    parser = argparse.ArgumentParser(description="Utilitário de Backup e Restore do Prometeus")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup_parser = subparsers.add_parser("backup", help="Criar backup com hash SHA-256")
    backup_parser.add_argument(
        "--output", "-o", default="var/backups/prometeus_backup.json", help="Caminho do arquivo"
    )

    verify_parser = subparsers.add_parser("verify", help="Verificar integridade do backup")
    verify_parser.add_argument("--file", "-f", required=True, help="Caminho do arquivo de backup")

    restore_parser = subparsers.add_parser("restore", help="Restaurar backup na base")
    restore_parser.add_argument("--file", "-f", required=True, help="Caminho do arquivo de backup")
    restore_parser.add_argument(
        "--clean", action="store_true", default=True, help="Limpar dados existentes antes"
    )

    args = parser.parse_args()

    settings = AppSettings()
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    if args.command == "verify":
        is_ok = BackupRestoreManager.verify_integrity(args.file)
        if is_ok:
            print(f"[OK] Backup {args.file} é íntegro e autêntico.")
        else:
            print(f"[ERRO] Backup {args.file} está corrompido!")
            exit(1)
        return

    async with session_factory() as session:
        manager = BackupRestoreManager(session)
        if args.command == "backup":
            manifest = await manager.create_backup(args.output)
            print(f"[OK] Backup gerado: {manifest.total_records} registros em {args.output}")
        elif args.command == "restore":
            report = await manager.restore_backup(args.file, clean_existing=args.clean)
            print(f"[OK] Restauração concluída: {report['total_restored']} registros restaurados.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_cli())
