import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.mock_services.task_service import TaskService


@pytest.mark.asyncio
async def test_create_task_success(db_session: AsyncSession):
    service = TaskService(db_session)
    task = await service.create_task(
        title="Fix payment gateway bug",
        assignee="dev01",
        priority="High",
        description="Investigate stripe timeout",
    )

    assert task["task_id"] == "TASK-109"
    assert task["title"] == "Fix payment gateway bug"
    assert task["assignee"] == "dev01"
    assert task["status"] == "Open"
    assert task["priority"] == "High"


@pytest.mark.asyncio
async def test_create_task_invalid_assignee(db_session: AsyncSession):
    service = TaskService(db_session)
    with pytest.raises(ValueError, match="not an active team member"):
        await service.create_task(
            title="Invalid task",
            assignee="unknown_dev",
            priority="Low",
        )


@pytest.mark.asyncio
async def test_create_task_invalid_priority(db_session: AsyncSession):
    service = TaskService(db_session)
    with pytest.raises(ValueError, match="Invalid priority"):
        await service.create_task(
            title="Invalid task",
            assignee="dev01",
            priority="Urgent",
        )


@pytest.mark.asyncio
async def test_create_task_idempotency(db_session: AsyncSession):
    service = TaskService(db_session)
    key = "workflow-run-1:step-1"

    task1 = await service.create_task(
        title="Review PR",
        assignee="dev01",
        priority="Medium",
        idempotency_key=key,
    )

    task2 = await service.create_task(
        title="Review PR",
        assignee="dev01",
        priority="Medium",
        idempotency_key=key,
    )

    assert task1["task_id"] == task2["task_id"]
    all_tasks = await service.list_tasks()
    matching = [t for t in all_tasks if t.get("idempotency_key") == key]
    assert len(matching) == 1


@pytest.mark.asyncio
async def test_get_task(db_session: AsyncSession):
    service = TaskService(db_session)
    task = await service.get_task("TASK-101")
    assert task is not None
    assert task["task_id"] == "TASK-101"
    assert task["assignee"] == "dev01"

    missing = await service.get_task("TASK-999")
    assert missing is None


@pytest.mark.asyncio
async def test_update_task(db_session: AsyncSession):
    service = TaskService(db_session)
    updated = await service.update_task(
        "TASK-101",
        {"status": "In Progress", "priority": "Highest"},
    )
    assert updated["status"] == "In Progress"
    assert updated["priority"] == "Highest"


@pytest.mark.asyncio
async def test_update_task_invalid_assignee(db_session: AsyncSession):
    service = TaskService(db_session)
    with pytest.raises(ValueError, match="not an active team member"):
        await service.update_task("TASK-101", {"assignee": "ghost_dev"})


@pytest.mark.asyncio
async def test_list_tasks_overdue(db_session: AsyncSession):
    service = TaskService(db_session)
    overdue = await service.list_tasks(
        priority="High",
        is_overdue=True,
        reference_date="2026-10-25",
    )
    assert len(overdue) >= 3
    task_ids = [t["task_id"] for t in overdue]
    assert "TASK-101" in task_ids
    assert "TASK-104" in task_ids
    assert "TASK-106" in task_ids


@pytest.mark.asyncio
async def test_list_tasks_with_limit(db_session: AsyncSession):
    service = TaskService(db_session)
    tasks = await service.list_tasks(limit=3)
    assert len(tasks) == 3
