from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config.env_config import get_settings
from app.services.mock_services.seed_data import seed_mock_data

settings = get_settings()

test_engine = create_async_engine(settings.POSTGRES_URL, poolclass=NullPool)
test_session_factory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_session_factory() as session:
        await seed_mock_data(session, reset=True)
        yield session
    await test_engine.dispose()
