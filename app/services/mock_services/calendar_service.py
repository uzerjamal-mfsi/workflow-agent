from typing import Any

from app.models.mock_models import CalendarEvent, TeamMember
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class CalendarService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def check_availability(self, user_id: str, date_str: str) -> dict[str, Any]:
        member = await self.session.get(TeamMember, user_id)
        if not member:
            raise ValueError(f"User '{user_id}' not found in team directory")

        stmt = select(CalendarEvent).where(
            CalendarEvent.user_id == user_id,
            CalendarEvent.start_time.startswith(date_str),
        )
        events = (await self.session.scalars(stmt)).all()

        return {
            "user_id": user_id,
            "date": date_str,
            "available": len(events) == 0,
            "busy_events": [
                {
                    "event_id": ev.event_id,
                    "title": ev.title,
                    "start": ev.start_time,
                    "end": ev.end_time,
                    "status": ev.status,
                }
                for ev in events
            ],
        }

    async def get_events(
        self, user_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        stmt = (
            select(CalendarEvent)
            .where(CalendarEvent.user_id == user_id)
            .limit(limit)
        )
        events = (await self.session.scalars(stmt)).all()
        return [
            {
                "event_id": ev.event_id,
                "user_id": ev.user_id,
                "title": ev.title,
                "start": ev.start_time,
                "end": ev.end_time,
                "status": ev.status,
            }
            for ev in events
        ]
