from collections.abc import AsyncIterable

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config.env_config import get_settings

class Base(DeclarativeBase):
    """Base class for all database models"""
    pass

settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.POSTGRES_URL,
    echo=False,
    pool_size=10,
    max_overflow=5
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db_session() -> AsyncIterable[AsyncSession]:
    """FastAPI dependency to inject database sessions into ANY route or service"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise