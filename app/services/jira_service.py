"""Mock Jira service backed by PostgreSQL tasks table."""

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.config.db_config import get_sync_engine
from app.models import Base, Task

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_TASKS = DATA_DIR / "tasks.json"
DEFAULT_TEAM = DATA_DIR / "team_directory.json"


def _parse_due_date(val: Any) -> date | None:
    if isinstance(val, date):
        return val
    if isinstance(val, str) and val.strip():
        try:
            return date.fromisoformat(val.strip()[:10])
        except ValueError:
            return None
    return None


def seed_mock_data(tasks_path: str | Path = DEFAULT_TASKS, engine=None) -> None:
    """Read tasks.json and insert initial tasks using ON CONFLICT DO NOTHING."""
    path = Path(tasks_path)
    if not path.exists():
        return
    raw_tasks = json.loads(path.read_text(encoding="utf-8"))
    if not raw_tasks:
        return

    eng = engine or get_sync_engine()
    Base.metadata.create_all(eng)

    rows = [
        {
            "id": t.get("task_id") or t.get("id"),
            "title": t.get("title", ""),
            "assignee": t.get("assignee", "dev01"),
            "status": t.get("status", "Open"),
            "priority": t.get("priority", "Medium"),
            "due_date": _parse_due_date(t.get("due_date")),
            "updated_at": datetime.now(timezone.utc),
        }
        for t in raw_tasks
        if t.get("task_id") or t.get("id")
    ]

    with Session(eng) as session:
        if eng.dialect.name == "postgresql":
            stmt = pg_insert(Task).values(rows).on_conflict_do_nothing(index_elements=["id"])
            session.execute(stmt)
        else:
            for row in rows:
                if not session.get(Task, row["id"]):
                    session.add(Task(**row))
        session.commit()


def reset_mock_data(tasks_path: str | Path = DEFAULT_TASKS, engine=None) -> None:
    """Reset tasks table and reseed with clean copy of tasks.json."""
    eng = engine or get_sync_engine()
    Base.metadata.create_all(eng)
    with Session(eng) as session:
        session.execute(delete(Task))
        session.commit()
    seed_mock_data(tasks_path=tasks_path, engine=eng)


class JiraService:
    """Jira service backed by PostgreSQL tasks table."""

    def __init__(
        self,
        tasks_path: str | Path = DEFAULT_TASKS,
        team_path: str | Path = DEFAULT_TEAM,
        engine=None,
    ) -> None:
        self.tasks_path = Path(tasks_path)
        self.team_path = Path(team_path)
        self.engine = engine or get_sync_engine()
        seed_mock_data(tasks_path=self.tasks_path, engine=self.engine)

    def _get_active_users(self) -> set[str]:
        if not self.team_path.exists():
            return set()
        data = json.loads(self.team_path.read_text(encoding="utf-8"))
        return {u["user_id"] for u in data.get("users", []) if u.get("active", True)}

    def _next_task_id(self, session: Session) -> str:
        tasks = session.scalars(select(Task.id)).all()
        nums = [
            int(tid.split("-")[1])
            for tid in tasks
            if tid.startswith("TASK-") and tid.split("-")[1].isdigit()
        ]
        return f"TASK-{max(nums, default=100) + 1}"

    def _task_to_dict(self, task: Task, **extra: Any) -> dict[str, Any]:
        return {
            "id": task.id,
            "task_id": task.id,
            "title": task.title,
            "assignee": task.assignee,
            "priority": task.priority,
            "status": task.status,
            "due_date": str(task.due_date) if task.due_date else None,
            "project": extra.pop("project", "PLAT"),
            **extra,
        }

    def create_task(
        self, title: str, assignee: str, priority: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Create a new task in tasks table."""
        if not title or not title.strip():
            raise ValueError("Task title is required")
        if not assignee or assignee not in self._get_active_users():
            raise ValueError(f"Assignee '{assignee}' not found in team directory")

        with Session(self.engine) as session:
            task_id = kwargs.pop("task_id", None) or self._next_task_id(session)
            status = kwargs.pop("status", "Open")
            due_date = _parse_due_date(kwargs.pop("due_date", None))

            task = Task(
                id=task_id,
                title=title.strip(),
                assignee=assignee,
                priority=priority,
                status=status,
                due_date=due_date,
                updated_at=datetime.now(timezone.utc),
            )
            session.add(task)
            session.commit()
            return self._task_to_dict(task, **kwargs)

    def update_task(self, task_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        """Update fields on an existing task."""
        if not task_id or not task_id.strip():
            raise ValueError("Task ID is missing")
        if not isinstance(fields, dict):
            raise ValueError("Fields must be a dictionary")

        if "assignee" in fields and fields["assignee"] not in self._get_active_users():
            raise ValueError(
                f"Assignee '{fields['assignee']}' not found in team directory"
            )

        clean_id = task_id.strip()
        with Session(self.engine) as session:
            task = session.get(Task, clean_id)
            if not task:
                raise ValueError(f"Task with ID '{clean_id}' not found")

            for k, v in fields.items():
                if k == "due_date":
                    task.due_date = _parse_due_date(v)
                elif hasattr(task, k):
                    setattr(task, k, v)
            task.updated_at = datetime.now(timezone.utc)
            session.commit()
            return self._task_to_dict(task)

    def list_tasks(self, **filters: Any) -> list[dict[str, Any]]:
        """List tasks matching exact key-value criteria."""
        with Session(self.engine) as session:
            query = select(Task)
            if "task_id" in filters:
                query = query.where(Task.id == filters.pop("task_id"))
            if "id" in filters:
                query = query.where(Task.id == filters.pop("id"))
            if "assignee" in filters:
                query = query.where(Task.assignee == filters.pop("assignee"))
            if "status" in filters:
                query = query.where(Task.status == filters.pop("status"))
            if "priority" in filters:
                query = query.where(Task.priority == filters.pop("priority"))
            tasks = session.scalars(query).all()
            return [self._task_to_dict(t) for t in tasks]

    def get_overdue_high_priority_tasks(
        self, as_of: str | date | None = None
    ) -> list[dict[str, Any]]:
        """Filter for High/Highest priority tasks overdue relative to as_of date."""
        as_of_date = (
            as_of
            if isinstance(as_of, date)
            else _parse_due_date(as_of) or date.today()
        )
        with Session(self.engine) as session:
            query = (
                select(Task)
                .where(Task.priority.in_(["High", "Highest"]))
                .where(Task.status.not_in(["Done", "Cancelled"]))
                .where(Task.due_date.is_not(None))
                .where(Task.due_date < as_of_date)
            )
            tasks = session.scalars(query).all()
            return [self._task_to_dict(t) for t in tasks]


_default_jira_service = JiraService()
create_task = _default_jira_service.create_task
update_task = _default_jira_service.update_task
list_tasks = _default_jira_service.list_tasks
get_overdue_high_priority_tasks = _default_jira_service.get_overdue_high_priority_tasks
