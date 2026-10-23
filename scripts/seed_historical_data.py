"""Script de Semeadura da Base Histórica Canônica da ENS (Escola de Negócios e Seguros).

Popula as tabelas `historical_courses` e `historical_funnel_records` no PostgreSQL
com 5 cursos sintéticos de alta fidelidade em segmentos distintos da ENS e ofertas de 2 anos (2024 e 2025).

Uso:
    python scripts/seed_historical_data.py [--tenant ens] [--reset]
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from prometeus.infrastructure.db.session import get_session
from prometeus.infrastructure.institutional.ens.seeder import seed_historical_courses

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("prometeus.seed_historical")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Semeadura da base histórica de cursos e funil")
    parser.add_argument("--tenant", default="ens", help="Identificador do tenant (padrão: ens)")
    parser.add_argument("--reset", action="store_true", help="Limpar dados prévios do tenant antes de semear")
    args = parser.parse_args()

    logger.info(f"Iniciando semeadura de dados históricos para o tenant '{args.tenant}'...")
    async with get_session() as session:
        stats = await seed_historical_courses(session, tenant_id=args.tenant, reset=args.reset)

    print("\n" + "=" * 70)
    print(" BASE HISTÓRICA ENS POVOADA COM SUCESSO NO POSTGRESQL")
    print("=" * 70)
    print(f" • Tenant: {stats['tenant_id']}")
    print(f" • Cursos criados: {stats['courses_created']}")
    print(f" • Cursos atualizados: {stats['courses_updated']}")
    print(f" • Total de cursos no catálogo: {stats['total_courses']}")
    print(f" • Registros temporais de funil criados: {stats['funnel_records_processed']}")
    print(f" • Matrículas acumuladas no histórico: {stats['total_historical_enrolled']:,} alunos")
    print(f" • Receita total agregada: R$ {stats['total_historical_revenue_brl']:,.2f}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
