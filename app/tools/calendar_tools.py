from typing import Any

from langchain_core.tools import tool

from app.services.calendar_service import check_calendar_availability


@tool("check_calendar_availability")
def check_calendar_availability_tool(
    user_id: str = "",
    date: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """Check calendar availability for a user on a given date."""
    return check_calendar_availability(user_id=user_id, date=date, **kwargs)


__all__ = ["check_calendar_availability_tool"]
