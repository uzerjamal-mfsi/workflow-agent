"""LangChain tool wrappers for the mock Jira service."""

from typing import Any

from langchain_core.tools import tool

from app.services.jira_service import (
    create_task,
    get_overdue_high_priority_tasks,
    list_tasks,
    update_task,
)


@tool("create_task")
def create_task_tool(
    title: str,
    assignee: str = "dev01",
    priority: str = "Medium",
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a new task in Jira."""
    return create_task(title=title, assignee=assignee, priority=priority, **kwargs)


@tool("update_task")
def update_task_tool(
    task_id: str = "",
    fields: dict[str, Any] | None = None,
    filter: str | None = None,
    **kwargs: Any,
) -> dict[str, Any] | list[dict[str, Any]]:
    """Update fields on an existing task or bulk-update overdue tasks."""
    update_data = dict(fields or {})
    update_data.update(kwargs)

    if filter == "overdue_high_priority":
        overdue_tasks = get_overdue_high_priority_tasks()
        results = []
        for task in overdue_tasks:
            tid = task.get("task_id")
            if tid:
                results.append(update_task(task_id=tid, fields=dict(update_data)))
        return results

    if not task_id:
        raise ValueError("Task ID is missing")

    return update_task(task_id=task_id, fields=update_data)


@tool("list_tasks")
def list_tasks_tool(
    task_id: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
) -> list[dict[str, Any]]:
    """List and filter tasks from Jira matching criteria."""
    filters: dict[str, Any] = {}
    if task_id:
        filters["task_id"] = task_id
    if status:
        filters["status"] = status
    if priority:
        filters["priority"] = priority
    if assignee:
        filters["assignee"] = assignee
    return list_tasks(**filters)


__all__ = [
    "create_task_tool",
    "update_task_tool",
    "list_tasks_tool",
]
