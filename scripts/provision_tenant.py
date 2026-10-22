"""CLI de provisionamento, validação e onboarding de instituições white-label (Fase 09)."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from prometeus.domain.configuration import (
    load_scoring_profile,
    load_tenant_config,
)
from prometeus.infrastructure.institutional.factory import create_institutional_adapter

logger = logging.getLogger("prometeus.operations.onboarding")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


async def validate_tenant(tenant_path: str, scoring_path: str | None = None) -> bool:
    """Valida integridade do arquivo de tenant e do perfil de scoring associado."""
    logger.info(f"Validando configuração do tenant: {tenant_path}")
    try:
        tenant_cfg = load_tenant_config(tenant_path)
        logger.info(
            f"Tenant '{tenant_cfg.institution.id}' ({tenant_cfg.institution.display_name}) validado com sucesso!"
        )
        logger.info(
            f"Branding: {tenant_cfg.branding.product_name} — {tenant_cfg.branding.product_descriptor}"
        )
        logger.info(f"Adaptador configurado: {tenant_cfg.adapters.institutional}")

        # Testa criação do adaptador correspondente
        adapter = create_institutional_adapter(tenant_cfg.adapters.institutional)
        logger.info(f"Adaptador '{type(adapter).__name__}' instanciado com sucesso!")

        if scoring_path:
            logger.info(f"Validando perfil de scoring: {scoring_path}")
            scoring_cfg = load_scoring_profile(scoring_path)
            logger.info(
                f"Perfil '{scoring_cfg.profile_id}' validado! Soma de pesos = {sum(scoring_cfg.weights.values()):.2f}"
            )

        print(
            "\n[SUCESSO] Configuração institucional white-label 100% válida e pronta para homologação.\n"
        )
        return True
    except Exception as exc:
        logger.error(f"Erro na validação do tenant: {exc}")
        print(f"\n[ERRO] Falha de validação do tenant: {exc}\n")
        return False


async def check_adapter_health(adapter_name: str) -> bool:
    """Verifica conectividade e prontidão de um conector institucional."""
    try:
        adapter = create_institutional_adapter(adapter_name)
        status = await adapter.healthcheck()
        logger.info(
            f"Healthcheck [{status.adapter_name}]: {status.status.upper()} (latência: {status.latency_ms}ms) — {status.message}"
        )
        return status.status in ("ok", "degraded")
    except Exception as exc:
        logger.error(f"Falha ao executar healthcheck no adaptador '{adapter_name}': {exc}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Provisionamento e Onboarding White-Label Prometeus"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    val_parser = subparsers.add_parser(
        "validate", help="Validar schemas e regras de negócio do tenant"
    )
    val_parser.add_argument(
        "--tenant-config", "-t", required=True, help="Caminho do YAML do tenant"
    )
    val_parser.add_argument("--scoring-profile", "-s", help="Caminho do YAML de scoring")

    health_parser = subparsers.add_parser("check-adapter", help="Testar adaptador institucional")
    health_parser.add_argument(
        "--adapter", "-a", required=True, help="Nome do adaptador (ex: ens, infnet, mock)"
    )

    args = parser.parse_args()

    if args.command == "validate":
        success = asyncio.run(validate_tenant(args.tenant_config, args.scoring_profile))
        sys.exit(0 if success else 1)
    elif args.command == "check-adapter":
        success = asyncio.run(check_adapter_health(args.adapter))
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
