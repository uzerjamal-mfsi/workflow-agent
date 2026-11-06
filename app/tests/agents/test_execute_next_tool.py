from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.nodes.execute_new_tool import _run_tool, execute_next_tool
from app.schemas.core_schemas.tool_schemas import (
    CheckCalendarArgs,
    CreateTaskArgs,
    SearchTemplatesArgs,
    SendNotificationArgs,
    UpdateTaskArgs,
)
from app.schemas.state import Plan, Step, WorkflowState


@pytest.mark.asyncio
async def test_execute_next_tool_no_plan():
    state: WorkflowState = {"plan": None}
    result = await execute_next_tool(state)
    assert result == {"last_step_result": None}


@pytest.mark.asyncio
async def test_execute_next_tool_missing_plan():
    state: WorkflowState = {}
    result = await execute_next_tool(state)
    assert result == {"last_step_result": None}


@pytest.mark.asyncio
async def test_execute_next_tool_index_out_of_bounds():
    step = Step(
        step_id="step_1",
        title="Create Task",
        tool="create_task",
        args=CreateTaskArgs(title="Task 1", assignee="dev01"),
    )
    plan = Plan(reasoning="Test", steps=[step])
    state: WorkflowState = {"plan": plan, "current_step_index": 5}
    result = await execute_next_tool(state)
    assert result == {"last_step_result": None}


@pytest.mark.asyncio
async def test_execute_next_tool_success():
    step = Step(
        step_id="step_1",
        title="Create Task",
        tool="create_task",
        args=CreateTaskArgs(title="Task 1", assignee="dev01"),
    )
    plan = Plan(reasoning="Test", steps=[step])
    state: WorkflowState = {
        "plan": plan,
        "current_step_index": 0,
        "thread_id": "thread-123",
    }

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session_ctx = MagicMock()
    mock_session_ctx.__aenter__.return_value = mock_session
    mock_session_ctx.__aexit__.return_value = None

    expected_output = {"task_id": "TASK-101", "status": "Open"}

    with (
        patch(
            "app.agents.nodes.execute_new_tool.async_session_factory",
            return_value=mock_session_ctx,
        ),
        patch(
            "app.agents.nodes.execute_new_tool._run_tool",
            new_callable=AsyncMock,
            return_value=expected_output,
        ) as mock_run,
    ):
        result = await execute_next_tool(state)

        assert result == {
            "last_step_result": {
                "step_id": "step_1",
                "tool": "create_task",
                "success": True,
                "output": expected_output,
                "error": None,
            }
        }
        mock_run.assert_awaited_once_with(step, "thread-123", mock_session)


@pytest.mark.asyncio
async def test_execute_next_tool_exception():
    step = Step(
        step_id="step_1",
        title="Create Task",
        tool="create_task",
        args=CreateTaskArgs(title="Task 1", assignee="dev01"),
    )
    plan = Plan(reasoning="Test", steps=[step])
    state: WorkflowState = {"plan": plan, "current_step_index": 0}

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session_ctx = MagicMock()
    mock_session_ctx.__aenter__.return_value = mock_session
    mock_session_ctx.__aexit__.return_value = None

    with (
        patch(
            "app.agents.nodes.execute_new_tool.async_session_factory",
            return_value=mock_session_ctx,
        ),
        patch(
            "app.agents.nodes.execute_new_tool._run_tool",
            side_effect=RuntimeError("Service unavailable"),
        ),
    ):
        result = await execute_next_tool(state)

        assert result == {
            "last_step_result": {
                "step_id": "step_1",
                "tool": "create_task",
                "success": False,
                "output": None,
                "error": "Service unavailable",
            }
        }


@pytest.mark.asyncio
async def test_run_tool_create_task():
    step = Step(
        step_id="step_1",
        title="Create Task",
        tool="create_task",
        args=CreateTaskArgs(title="New Bug", assignee="dev01", priority="High"),
    )
    session = AsyncMock(spec=AsyncSession)
    mock_task_service = MagicMock()
    mock_task_service.create_task = AsyncMock(return_value={"task_id": "TASK-102"})

    with patch("app.agents.nodes.execute_new_tool.TaskService", return_value=mock_task_service):
        output = await _run_tool(step, "thread-abc", session)

        assert output == {"task_id": "TASK-102"}
        mock_task_service.create_task.assert_awaited_once_with(
            title="New Bug",
            assignee="dev01",
            priority="High",
            idempotency_key="thread-abc:step_1",
        )


@pytest.mark.asyncio
async def test_run_tool_update_task():
    step = Step(
        step_id="step_2",
        title="Update Task",
        tool="update_task",
        args=UpdateTaskArgs(task_id="TASK-101", fields={"status": "In Progress"}),
    )
    session = AsyncMock(spec=AsyncSession)
    mock_task_service = MagicMock()
    mock_task_service.update_task = AsyncMock(return_value={"task_id": "TASK-101", "status": "In Progress"})

    with patch("app.agents.nodes.execute_new_tool.TaskService", return_value=mock_task_service):
        output = await _run_tool(step, "thread-abc", session)

        assert output == {"task_id": "TASK-101", "status": "In Progress"}
        mock_task_service.update_task.assert_awaited_once_with(
            task_id="TASK-101",
            fields={"status": "In Progress"},
        )


@pytest.mark.asyncio
async def test_run_tool_send_notification():
    step = Step(
        step_id="step_3",
        title="Send Notification",
        tool="send_notification",
        args=SendNotificationArgs(recipient="pm01", message="Review needed"),
    )
    session = AsyncMock(spec=AsyncSession)
    mock_notif_service = MagicMock()
    mock_notif_service.send_notification = AsyncMock(return_value={"id": 1, "status": "Sent"})

    with patch("app.agents.nodes.execute_new_tool.NotificationService", return_value=mock_notif_service):
        output = await _run_tool(step, "thread-abc", session)

        assert output == {"id": 1, "status": "Sent"}
        mock_notif_service.send_notification.assert_awaited_once_with(
            recipient="pm01",
            message="Review needed",
            idempotency_key="thread-abc:step_3",
        )


@pytest.mark.asyncio
async def test_run_tool_check_calendar_availability():
    step = Step(
        step_id="step_4",
        title="Check Availability",
        tool="check_calendar_availability",
        args=CheckCalendarArgs(user_id="dev01", date="2026-11-07"),
    )
    session = AsyncMock(spec=AsyncSession)
    mock_cal_service = MagicMock()
    mock_cal_service.check_availability = AsyncMock(return_value={"user_id": "dev01", "available": True})

    with patch("app.agents.nodes.execute_new_tool.CalendarService", return_value=mock_cal_service):
        output = await _run_tool(step, "thread-abc", session)

        assert output == {"user_id": "dev01", "available": True}
        mock_cal_service.check_availability.assert_awaited_once_with(
            user_id="dev01",
            date_str="2026-11-07",
        )


@pytest.mark.asyncio
async def test_run_tool_search_workflow_templates():
    step = Step(
        step_id="step_5",
        title="Search Templates",
        tool="search_workflow_templates",
        args=SearchTemplatesArgs(query="deployment instructions"),
    )
    session = AsyncMock(spec=AsyncSession)
    mock_repo = MagicMock()
    mock_provider = MagicMock()
    mock_settings = MagicMock()
    mock_settings.QDRANT_COLLECTION = "workflow-sop"
    expected_sops = ["Template 1 content"]

    with (
        patch("app.agents.nodes.execute_new_tool.get_qdrant_repository", return_value=mock_repo),
        patch("app.agents.nodes.execute_new_tool.get_embedding_provider", return_value=mock_provider),
        patch("app.agents.nodes.execute_new_tool.get_settings", return_value=mock_settings),
        patch("app.agents.nodes.execute_new_tool.search_sops", return_value=expected_sops) as mock_search,
    ):
        output = await _run_tool(step, "thread-abc", session)

        assert output == expected_sops
        mock_search.assert_called_once_with(
            repository=mock_repo,
            embedding_provider=mock_provider,
            collection_name="workflow-sop",
            query="deployment instructions",
        )

