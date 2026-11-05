from typing import Any

from sqlalchemy import JSON, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config.postgres_config import Base


class TeamMember(Base):
    __tablename__: str = "team_members"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    team: Mapped[str] = mapped_column(String)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    permissions: Mapped[list[str]] = mapped_column(JSON, default=list)


class Task(Base):
    __tablename__: str = "tasks"

    task_id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    assignee: Mapped[str | None] = mapped_column(String, nullable=True)
    reporter: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="Open")
    priority: Mapped[str] = mapped_column(String, default="Medium")
    created_at: Mapped[str | None] = mapped_column(String, nullable=True)
    due_date: Mapped[str | None] = mapped_column(String, nullable=True)
    labels: Mapped[list[str]] = mapped_column(JSON, default=list)
    project: Mapped[str] = mapped_column(String, default="PLAT")
    comments: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    idempotency_key: Mapped[str | None] = mapped_column(
        String, unique=True, nullable=True, index=True
    )


class CalendarEvent(Base):
    __tablename__: str = "calendar_events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(String)
    start_time: Mapped[str] = mapped_column(String)
    end_time: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="busy")


class Notification(Base):
    __tablename__: str = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipient: Mapped[str] = mapped_column(String, index=True)
    subject: Mapped[str | None] = mapped_column(String, nullable=True)
    message: Mapped[str] = mapped_column(String)
    template_id: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="sent")
    idempotency_key: Mapped[str | None] = mapped_column(
        String, unique=True, nullable=True, index=True
    )
    created_at: Mapped[str | None] = mapped_column(String, nullable=True)
