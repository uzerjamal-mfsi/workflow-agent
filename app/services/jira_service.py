"""Minimal mock Jira service backed by tasks.json."""

import json
from datetime import date
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_TASKS = DATA_DIR / "tasks.json"
DEFAULT_TEAM = DATA_DIR / "team_directory.json"


class JiraService:
    """Mock Jira service backed by tasks.json"""

    def __init__(
        self,
        tasks_path: str | Path = DEFAULT_TASKS,
        team_path: str | Path = DEFAULT_TEAM,
    ) -> None:
        self.tasks_path = Path(tasks_path)
        self.team_path = Path(team_path)

    def _get_active_users(self) -> set[str]:
        if not self.team_path.exists():
            return set()
        data = json.loads(self.team_path.read_text(encoding="utf-8"))
        return {u["user_id"] for u in data.get("users", []) if u.get("active", True)}

    def _read_tasks(self) -> list[dict[str, Any]]:
        if not self.tasks_path.exists():
            return []
        return json.loads(self.tasks_path.read_text(encoding="utf-8"))

    def _write_tasks(self, tasks: list[dict[str, Any]]) -> None:
        self.tasks_path.parent.mkdir(parents=True, exist_ok=True)
        self.tasks_path.write_text(
            json.dumps(tasks, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _next_task_id(self, tasks: list[dict[str, Any]]) -> str:
        nums = [
            int(t["task_id"].split("-")[1])
            for t in tasks
            if t.get("task_id", "").startswith("TASK-")
            and t["task_id"].split("-")[1].isdigit()
        ]
        return f"TASK-{max(nums, default=100) + 1}"

    def create_task(
        self, title: str, assignee: str, priority: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Create a new task in tasks.json."""
        if not title or not title.strip():
            raise ValueError("Task title is required")
        if not assignee or assignee not in self._get_active_users():
            raise ValueError(f"Assignee '{assignee}' not found in team directory")

        tasks = self._read_tasks()
        task_id = kwargs.pop("task_id", None) or self._next_task_id(tasks)

        task = {
            "task_id": task_id,
            "title": title.strip(),
            "assignee": assignee,
            "priority": priority,
            "status": kwargs.pop("status", "Open"),
            "project": kwargs.pop("project", "PLAT"),
            **kwargs,
        }
        tasks.append(task)
        self._write_tasks(tasks)
        return task

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

        tasks = self._read_tasks()
        clean_id = task_id.strip()
        for task in tasks:
            if task.get("task_id") == clean_id:
                task.update(fields)
                self._write_tasks(tasks)
                return task

        raise ValueError(f"Task with ID '{clean_id}' not found")

    def list_tasks(self, **filters: Any) -> list[dict[str, Any]]:
        """List tasks matching exact key-value criteria."""
        tasks = self._read_tasks()
        return [
            t
            for t in tasks
            if all(t.get(k) == v for k, v in filters.items())
        ]

    def get_overdue_high_priority_tasks(
        self, as_of: str | date | None = None
    ) -> list[dict[str, Any]]:
        """Filter for High/Highest priority tasks overdue relative to as_of date."""
        today = str(as_of or date.today())
        tasks = self._read_tasks()
        return [
            t
            for t in tasks
            if t.get("priority") in {"High", "Highest"}
            and t.get("status") not in {"Done", "Cancelled"}
            and t.get("due_date")
            and str(t["due_date"]) < today
        ]


_default_jira_service = JiraService()
create_task = _default_jira_service.create_task
update_task = _default_jira_service.update_task
list_tasks = _default_jira_service.list_tasks
get_overdue_high_priority_tasks = _default_jira_service.get_overdue_high_priority_tasks
