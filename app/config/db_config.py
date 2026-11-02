"""Database engine and session configuration."""

import os
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config.env_config import settings

engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


def get_sync_database_url(url: str | None = None) -> str:
    db_url = url or os.getenv("SYNC_DATABASE_URL") or settings.DATABASE_URL
    if db_url.startswith("postgresql+asyncpg://"):
        return db_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    if db_url.startswith("postgresql://"):
        return db_url.replace("postgresql://", "postgresql+psycopg://")
    return db_url


_sync_engines: dict[str, Engine] = {}


def get_sync_engine(url: str | None = None) -> Engine:
    target_url = get_sync_database_url(url)
    if target_url not in _sync_engines:
        connect_args = (
            {"check_same_thread": False} if target_url.startswith("sqlite") else {}
        )
        _sync_engines[target_url] = create_engine(
            target_url, pool_pre_ping=True, connect_args=connect_args
        )
    return _sync_engines[target_url]


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield an async database session."""
    async with async_session_factory() as session:
        yield session


@contextmanager
def get_sync_db_session(engine_instance: Engine | None = None) -> Iterator[Session]:
    """Yield a synchronous database session."""
    eng = engine_instance or get_sync_engine()
    factory = sessionmaker(eng, expire_on_commit=False)
    with factory() as session:
        yield session
