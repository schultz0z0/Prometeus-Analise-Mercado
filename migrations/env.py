import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

# Adiciona src ao path para importar Base e modelos
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from prometeus.domain.configuration import AppSettings
from prometeus.infrastructure.db.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Obtém a URL do banco síncrona para Alembic (convertendo asyncpg para psycopg se necessário)."""
    settings = AppSettings()
    db_url = os.getenv("DATABASE_URL", settings.DATABASE_URL)
    # Converte driver assíncrono para síncrono no Alembic
    if db_url.startswith("postgresql+asyncpg://"):
        return db_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    if db_url.startswith("sqlite+aiosqlite://"):
        return db_url.replace("sqlite+aiosqlite://", "sqlite://", 1)
    return db_url


def run_migrations_offline() -> None:
    """Executa migrações no modo 'offline' gerando apenas SQL."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Executa migrações no modo 'online' conectado ao PostgreSQL."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Garante suporte a identificadores de revisão longos no PostgreSQL (VARCHAR 128)
        connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS alembic_version ("
                "  version_num VARCHAR(128) NOT NULL,"
                "  CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)"
                ")"
            )
        )
        connection.execute(
            text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)")
        )
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
