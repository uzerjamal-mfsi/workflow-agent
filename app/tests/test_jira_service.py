"""Unit tests for the minimal Mock Jira Service."""

import shutil
from datetime import date
from pathlib import Path

import pytest

from app.services.jira_service import (
    DEFAULT_TASKS,
    DEFAULT_TEAM,
    JiraService,
)


@pytest.fixture
def temp_jira(tmp_path: Path) -> JiraService:
    """Fixture providing an isolated JiraService backed by temporary data files."""
    temp_tasks = tmp_path / "tasks.json"
    temp_team = tmp_path / "team_directory.json"

    shutil.copyfile(DEFAULT_TASKS, temp_tasks)
    shutil.copyfile(DEFAULT_TEAM, temp_team)

    return JiraService(tasks_path=temp_tasks, team_path=temp_team)


def test_sample_tasks_file_unmodified(temp_jira: JiraService) -> None:
    """Verify tests do not dirty the original sample tasks.json file."""
    original_content = DEFAULT_TASKS.read_text(encoding="utf-8")

    temp_jira.create_task("Test isolation task", "dev01", "Low")
    temp_jira.update_task("TASK-101", {"status": "Closed"})

    after_content = DEFAULT_TASKS.read_text(encoding="utf-8")
    assert original_content == after_content


def test_create_task_success(temp_jira: JiraService) -> None:
    """Verify creating a task returns valid dict and auto-generates sequential ID."""
    task = temp_jira.create_task(
        title="Write integration tests",
        assignee="dev01",
        priority="High",
    )

    assert task["task_id"] == "TASK-109"
    assert task["title"] == "Write integration tests"
    assert task["assignee"] == "dev01"
    assert task["priority"] == "High"
    assert task["status"] == "Open"
    assert task["project"] == "PLAT"


def test_update_task_success(temp_jira: JiraService) -> None:
    """Verify updating fields on an existing task."""
    updated = temp_jira.update_task(
        "TASK-101",
        {"status": "In Progress", "priority": "Highest"},
    )

    assert updated["task_id"] == "TASK-101"
    assert updated["status"] == "In Progress"
    assert updated["priority"] == "Highest"

    # Re-read through list_tasks to confirm disk persistence
    tasks = temp_jira.list_tasks(task_id="TASK-101")
    assert len(tasks) == 1
    assert tasks[0]["status"] == "In Progress"


def test_list_tasks_filter(temp_jira: JiraService) -> None:
    """Verify filtering tasks by criteria."""
    dev01_tasks = temp_jira.list_tasks(assignee="dev01")
    assert len(dev01_tasks) >= 2
    assert all(t["assignee"] == "dev01" for t in dev01_tasks)

    open_tasks = temp_jira.list_tasks(status="Open")
    assert len(open_tasks) >= 1
    assert all(t["status"] == "Open" for t in open_tasks)


def test_get_overdue_high_priority_tasks(temp_jira: JiraService) -> None:
    """Verify overdue high-priority helper identifies matching tasks and excludes Done."""
    overdue = temp_jira.get_overdue_high_priority_tasks(as_of=date(2026, 11, 2))
    task_ids = {t["task_id"] for t in overdue}

    # TASK-101 (Open, High, 2026-10-22) should be included
    assert "TASK-101" in task_ids
    # TASK-102 (In Progress, High, 2026-10-28) should be included
    assert "TASK-102" in task_ids
    # TASK-105 (Done, Medium, 2026-10-16) should be excluded
    assert "TASK-105" not in task_ids
    # TASK-103 (Open, Medium, 2026-11-03) future date, excluded
    assert "TASK-103" not in task_ids


def test_create_task_validation_errors(temp_jira: JiraService) -> None:
    """Verify error cases when creating tasks."""
    # Missing title
    with pytest.raises(ValueError, match="Task title is required"):
        temp_jira.create_task("", "dev01", "High")

    # Missing / non-existent assignee
    with pytest.raises(ValueError, match="Assignee 'unknown_dev' not found"):
        temp_jira.create_task("Test", "unknown_dev", "High")

    with pytest.raises(ValueError, match="Assignee '' not found"):
        temp_jira.create_task("Test", "", "High")


def test_update_task_validation_errors(temp_jira: JiraService) -> None:
    """Verify error cases when updating tasks."""
    # Missing task ID
    with pytest.raises(ValueError, match="Task ID is missing"):
        temp_jira.update_task("", {"status": "Done"})

    # Non-existent task ID
    with pytest.raises(ValueError, match="Task with ID 'TASK-999' not found"):
        temp_jira.update_task("TASK-999", {"status": "Done"})

    # Invalid fields argument
    with pytest.raises(ValueError, match="Fields must be a dictionary"):
        temp_jira.update_task("TASK-101", ["not", "dict"])  # type: ignore[arg-type]

    # Updating to unknown assignee
    with pytest.raises(ValueError, match="Assignee 'invalid_user' not found"):
        temp_jira.update_task("TASK-101", {"assignee": "invalid_user"})
