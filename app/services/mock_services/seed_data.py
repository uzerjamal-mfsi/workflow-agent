import json
from pathlib import Path
from typing import Any

from app.config.postgres_config import Base, engine
from app.models.mock_models import CalendarEvent, Notification, Task, TeamMember
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

DATA_DIR = Path("app/data")


async def init_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_mock_data(session: AsyncSession, reset: bool = False) -> dict[str, Any]:
    if reset:
        await session.execute(delete(Notification))
        await session.execute(delete(CalendarEvent))
        await session.execute(delete(Task))
        await session.execute(delete(TeamMember))
        await session.commit()
    else:
        existing = await session.scalar(select(TeamMember.user_id).limit(1))
        if existing:
            return {"status": "already_seeded"}

    counts = {"team_members": 0, "tasks": 0, "calendar_events": 0}

    team_file = DATA_DIR / "team_directory.json"
    if team_file.exists():
        data = json.loads(team_file.read_text(encoding="utf-8"))
        for user in data.get("users", []):
            member = TeamMember(
                user_id=user["user_id"],
                name=user["name"],
                email=user["email"],
                role=user["role"],
                team=user["team"],
                active=user.get("active", True),
                permissions=user.get("permissions", []),
            )
            session.add(member)
            counts["team_members"] += 1

    tasks_file = DATA_DIR / "tasks.json"
    if tasks_file.exists():
        tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
        for t in tasks:
            task = Task(
                task_id=t["task_id"],
                title=t["title"],
                description=t.get("description"),
                assignee=t.get("assignee"),
                reporter=t.get("reporter"),
                status=t.get("status", "Open"),
                priority=t.get("priority", "Medium"),
                created_at=t.get("created_at"),
                due_date=t.get("due_date"),
                labels=t.get("labels", []),
                project=t.get("project", "PLAT"),
                comments=t.get("comments", []),
            )
            session.add(task)
            counts["tasks"] += 1

    cal_file = DATA_DIR / "calendar_events.json"
    if cal_file.exists():
        cal_data = json.loads(cal_file.read_text(encoding="utf-8"))
        users_events = cal_data.get("users", {})
        for user_id, events in users_events.items():
            for ev in events:
                event = CalendarEvent(
                    event_id=ev["event_id"],
                    user_id=user_id,
                    title=ev["title"],
                    start_time=ev["start"],
                    end_time=ev["end"],
                    status=ev.get("status", "busy"),
                )
                session.add(event)
                counts["calendar_events"] += 1

    await session.commit()
    return counts
