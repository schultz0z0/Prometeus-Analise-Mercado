"""Configuração de sessão e conexão assíncrona com PostgreSQL via SQLAlchemy e asyncpg."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from prometeus.domain.configuration import AppSettings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine(database_url: str | None = None, **engine_kwargs: Any) -> AsyncEngine:
    """Retorna a engine assíncrona singleton ou configurada sob demanda."""
    global _engine
    if database_url is not None:
        return create_async_engine(database_url, **engine_kwargs)

    if _engine is None:
        settings = AppSettings()
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            future=True,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory(
    engine: AsyncEngine | None = None,
    database_url: str | None = None,
) -> async_sessionmaker[AsyncSession]:
    """Retorna o sessionmaker assíncrono."""
    global _session_factory
    if engine is not None:
        return async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

    if database_url is not None:
        eng = get_engine(database_url)
        return async_sessionmaker(bind=eng, expire_on_commit=False, class_=AsyncSession)

    if _session_factory is None:
        eng = get_engine()
        _session_factory = async_sessionmaker(bind=eng, expire_on_commit=False, class_=AsyncSession)
    return _session_factory


@asynccontextmanager
async def get_session(
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """Gerenciador de contexto para transações assíncronas."""
    factory = session_factory or get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependência para injeção no FastAPI."""
    async with get_session() as session:
        yield session
