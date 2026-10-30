import shutil
from pathlib import Path

import pytest

from app.services.calendar_service import (
    DEFAULT_CALENDAR,
    CalendarService,
)
from app.tools.calendar_tools import check_calendar_availability_tool


@pytest.fixture
def temp_calendar_service(tmp_path: Path) -> CalendarService:
    """Fixture providing isolated CalendarService backed by temporary data file."""
    temp_cal = tmp_path / "calendar_events.json"
    shutil.copyfile(DEFAULT_CALENDAR, temp_cal)
    return CalendarService(calendar_path=temp_cal)


def test_check_calendar_availability_busy_date(
    temp_calendar_service: CalendarService,
) -> None:
    """Verify user with scheduled events is flagged unavailable when no slot specified."""
    res = temp_calendar_service.check_calendar_availability("dev01", "2026-10-27")
    assert res["user_id"] == "dev01"
    assert res["date"] == "2026-10-27"
    assert res["available"] is False
    assert len(res["events"]) == 2
    assert len(res["conflicts"]) == 2


def test_check_calendar_availability_free_date(
    temp_calendar_service: CalendarService,
) -> None:
    """Verify user with no scheduled events on date is flagged available."""
    res = temp_calendar_service.check_calendar_availability("dev01", "2026-10-29")
    assert res["user_id"] == "dev01"
    assert res["date"] == "2026-10-29"
    assert res["available"] is True
    assert len(res["events"]) == 0
    assert len(res["conflicts"]) == 0


def test_check_calendar_availability_time_slot_overlap(
    temp_calendar_service: CalendarService,
) -> None:
    """Verify specific overlapping slot flags conflict."""
    res = temp_calendar_service.check_calendar_availability(
        "dev01",
        "2026-10-27",
        start_time="10:00",
        end_time="10:30",
    )
    assert res["available"] is False
    assert len(res["conflicts"]) == 1
    assert res["conflicts"][0]["event_id"] == "CAL-2001"


def test_check_calendar_availability_time_slot_free(
    temp_calendar_service: CalendarService,
) -> None:
    """Verify specific open slot flags availability."""
    res = temp_calendar_service.check_calendar_availability(
        "dev01",
        "2026-10-27",
        start_time="12:00",
        end_time="13:00",
    )
    assert res["available"] is True
    assert len(res["conflicts"]) == 0


def test_check_calendar_availability_validation_errors(
    temp_calendar_service: CalendarService,
) -> None:
    """Verify error cases for missing or unknown user ID."""
    with pytest.raises(ValueError, match="user_id is required"):
        temp_calendar_service.check_calendar_availability("")

    with pytest.raises(ValueError, match="User 'unknown_user' not found in calendar"):
        temp_calendar_service.check_calendar_availability("unknown_user", "2026-10-27")


def test_calendar_tool_wrapper() -> None:
    """Verify LangChain tool wrapper invokes calendar availability check."""
    res = check_calendar_availability_tool.invoke(
        {"user_id": "dev02", "date": "2026-10-28"}
    )
    assert res["user_id"] == "dev02"
    assert "available" in res
    assert res["status"] == "success"
