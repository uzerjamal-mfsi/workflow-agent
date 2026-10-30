import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_CALENDAR = DATA_DIR / "calendar_events.json"


class CalendarService:
    """Service for checking user schedule and availability from calendar events."""

    def __init__(self, calendar_path: str | Path = DEFAULT_CALENDAR) -> None:
        self.calendar_path = Path(calendar_path)

    def _read_calendar(self) -> dict[str, Any]:
        if not self.calendar_path.exists():
            return {"users": {}}
        return json.loads(self.calendar_path.read_text(encoding="utf-8"))

    def check_calendar_availability(
        self,
        user_id: str,
        date: str = "",
        start_time: str | None = None,
        end_time: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Check calendar availability for a user on a given date or time slot."""
        if not user_id or not user_id.strip():
            raise ValueError("user_id is required")

        data = self._read_calendar()
        users_calendar = data.get("users", {})
        if user_id not in users_calendar:
            raise ValueError(f"User '{user_id}' not found in calendar")

        user_events = users_calendar.get(user_id, [])
        target_date = date.strip().split("T")[0].split(" ")[0] if date else "2026-10-27"

        day_events = [
            e for e in user_events if e.get("start", "").startswith(target_date)
        ]

        req_start = start_time or kwargs.get("start")
        req_end = end_time or kwargs.get("end")

        if req_start:
            if "T" in str(req_start):
                w_start = datetime.fromisoformat(str(req_start))
            else:
                raw_time = str(req_start)
                time_str = (
                    f"{raw_time}:00" if len(raw_time.split(":")) == 2 else raw_time
                )
                w_start = datetime.fromisoformat(f"{target_date}T{time_str}")

            if req_end:
                if "T" in str(req_end):
                    w_end = datetime.fromisoformat(str(req_end))
                else:
                    raw_time = str(req_end)
                    time_str = (
                        f"{raw_time}:00" if len(raw_time.split(":")) == 2 else raw_time
                    )
                    w_end = datetime.fromisoformat(f"{target_date}T{time_str}")
            else:
                w_end = w_start + timedelta(minutes=30)

            conflicts = []
            for ev in day_events:
                ev_start = datetime.fromisoformat(ev["start"])
                ev_end = datetime.fromisoformat(ev["end"])
                if w_start.tzinfo is None and ev_start.tzinfo is not None:
                    ev_start = ev_start.replace(tzinfo=None)
                    ev_end = ev_end.replace(tzinfo=None)
                elif w_start.tzinfo is not None and ev_start.tzinfo is None:
                    w_start = w_start.replace(tzinfo=None)
                    w_end = w_end.replace(tzinfo=None)

                if w_start < ev_end and ev_start < w_end and ev.get("status") == "busy":
                    conflicts.append(ev)

            available = len(conflicts) == 0
        else:
            conflicts = [e for e in day_events if e.get("status") == "busy"]
            available = len(conflicts) == 0

        return {
            "user_id": user_id,
            "date": target_date,
            "available": available,
            "events": day_events,
            "conflicts": conflicts,
            "status": "success",
        }


_default_calendar_service = CalendarService()
check_calendar_availability = _default_calendar_service.check_calendar_availability
