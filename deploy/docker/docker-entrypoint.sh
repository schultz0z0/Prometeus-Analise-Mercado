#!/bin/sh
set -e

# Executa migrações automáticas se a variável AUTO_MIGRATE estiver habilitada
if [ "$AUTO_MIGRATE" = "true" ]; then
    echo "[prometeus-entrypoint] Aplicando migrações do banco de dados (Alembic)..."
    alembic upgrade head
    echo "[prometeus-entrypoint] Migrações concluídas com sucesso."
fi

# Executa o comando principal do container
exec "$@"
