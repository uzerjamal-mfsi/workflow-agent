import asyncio

from app.config.postgres_config import async_session_factory, engine
from app.services.mock_services.seed_data import init_tables, seed_mock_data


async def main():
    await init_tables()
    async with async_session_factory() as session:
        result = await seed_mock_data(session, reset=True)
        print("Seed completed:", result)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
