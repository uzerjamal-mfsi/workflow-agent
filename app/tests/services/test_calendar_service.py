import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.mock_services.calendar_service import CalendarService


@pytest.mark.asyncio
async def test_check_availability_busy(db_session: AsyncSession):
    service = CalendarService(db_session)
    result = await service.check_availability("dev01", "2026-10-27")

    assert result["user_id"] == "dev01"
    assert result["available"] is False
    assert len(result["busy_events"]) == 2
    titles = [e["title"] for e in result["busy_events"]]
    assert "Payments API review" in titles
    assert "Platform stand-up" in titles


@pytest.mark.asyncio
async def test_check_availability_free(db_session: AsyncSession):
    service = CalendarService(db_session)
    result = await service.check_availability("dev01", "2026-10-31")

    assert result["user_id"] == "dev01"
    assert result["available"] is True
    assert len(result["busy_events"]) == 0


@pytest.mark.asyncio
async def test_check_availability_invalid_user(db_session: AsyncSession):
    service = CalendarService(db_session)
    with pytest.raises(ValueError, match="not found in team directory"):
        await service.check_availability("unknown_user", "2026-10-27")


@pytest.mark.asyncio
async def test_get_events(db_session: AsyncSession):
    service = CalendarService(db_session)
    events = await service.get_events("dev01")
    assert len(events) == 3


@pytest.mark.asyncio
async def test_get_events_with_limit(db_session: AsyncSession):
    service = CalendarService(db_session)
    events = await service.get_events("dev01", limit=1)
    assert len(events) == 1
