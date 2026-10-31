import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.agents.workflow_agent import (
    create_workflow_graph,
    execute_next_tool,
    verify_step,
)
from app.schemas.workflow import AgentState, ExecutionPlan, PlanStep
from app.services.calendar_service import (
    DEFAULT_CALENDAR,
    CalendarService,
)
from app.services.jira_service import (
    DEFAULT_TASKS,
    DEFAULT_TEAM,
    JiraService,
)
from app.services.notification_service import (
    DEFAULT_TEMPLATES,
    NotificationService,
)


@pytest.fixture
def isolated_services(tmp_path: Path):
    """Provide isolated service instances backed by copied test files."""
    temp_tasks = tmp_path / "tasks.json"
    temp_team = tmp_path / "team_directory.json"
    temp_cal = tmp_path / "calendar_events.json"
    temp_tpl = tmp_path / "notification_templates.json"

    shutil.copyfile(DEFAULT_TASKS, temp_tasks)
    shutil.copyfile(DEFAULT_TEAM, temp_team)
    shutil.copyfile(DEFAULT_CALENDAR, temp_cal)
    shutil.copyfile(DEFAULT_TEMPLATES, temp_tpl)

    jira = JiraService(tasks_path=temp_tasks, team_path=temp_team)
    notif = NotificationService(team_path=temp_team, templates_path=temp_tpl)
    cal = CalendarService(calendar_path=temp_cal)

    return {"jira": jira, "notif": notif, "cal": cal}


def test_execute_next_tool_notification(isolated_services):
    """Verify execute_next_tool executes send_notification."""
    step = PlanStep(
        step_id="step_notify",
        action="Notify PM about task assignment",
        tool_name="send_notification",
        tool_args={"recipient": "pm01", "message": "Task TASK-101 is ready for review"},
    )
    state: AgentState = {
        "plan": [step],
        "pending_steps": ["step_notify"],
        "completed_steps": [],
        "failed_steps": [],
        "step_results": {},
    }

    result = execute_next_tool(
        state,
        notification_service_instance=isolated_services["notif"],
    )
    assert result["current_step_id"] == "step_notify"
    assert "step_notify" in result["step_results"]
    assert result["step_results"]["step_notify"]["status"] == "sent"
    assert result["step_results"]["step_notify"]["recipient"] == "pm01"


def test_execute_next_tool_calendar_check(isolated_services):
    """Verify execute_next_tool executes check_calendar_availability."""
    step = PlanStep(
        step_id="step_cal",
        action="Check availability for dev01",
        tool_name="check_calendar_availability",
        tool_args={"user_id": "dev01", "date": "2026-10-27"},
    )
    state: AgentState = {
        "plan": [step],
        "pending_steps": ["step_cal"],
        "completed_steps": [],
        "failed_steps": [],
        "step_results": {},
    }

    result = execute_next_tool(
        state,
        calendar_service_instance=isolated_services["cal"],
    )
    assert result["current_step_id"] == "step_cal"
    assert "step_cal" in result["step_results"]
    assert result["step_results"]["step_cal"]["user_id"] == "dev01"
    assert result["step_results"]["step_cal"]["status"] == "success"


def test_execute_next_tool_search_sops():
    """Verify execute_next_tool executes search_workflow_templates."""
    mock_retriever = MagicMock(return_value=[{"section_title": "Task creation"}])
    step = PlanStep(
        step_id="step_search",
        action="Search task SOPs",
        tool_name="search_workflow_templates",
        tool_args={"query": "task creation and assignment"},
    )
    state: AgentState = {
        "plan": [step],
        "pending_steps": ["step_search"],
        "completed_steps": [],
        "failed_steps": [],
        "step_results": {},
    }

    result = execute_next_tool(state, retriever_fn=mock_retriever)
    assert result["current_step_id"] == "step_search"
    assert "step_search" in result["step_results"]
    assert result["step_results"]["step_search"] == [{"section_title": "Task creation"}]


def test_execute_next_tool_failure_recorded():
    """Verify tool execution errors are caught and recorded as failed in results."""
    step = PlanStep(
        step_id="step_err",
        action="Notify invalid user",
        tool_name="send_notification",
        tool_args={"recipient": "nonexistent_dev", "message": "Hello"},
    )
    state: AgentState = {
        "plan": [step],
        "pending_steps": ["step_err"],
        "completed_steps": [],
        "failed_steps": [],
        "step_results": {},
    }

    result = execute_next_tool(state)
    assert result["current_step_id"] == "step_err"
    assert result["step_results"]["step_err"]["status"] == "failed"
    assert "error" in result["step_results"]["step_err"]

    verified = verify_step(
        {
            "plan": [step],
            "current_step_id": "step_err",
            "pending_steps": ["step_err"],
            "completed_steps": [],
            "failed_steps": [],
            "step_results": result["step_results"],
        }
    )
    assert "step_err" in verified["failed_steps"]
    assert verified["completed_steps"] == []
    assert step.status == "failed"


def test_graph_executes_all_new_tools(isolated_services):
    """Verify workflow graph executes a plan containing calendar, task, and notification steps."""
    plan_steps = [
        PlanStep(
            step_id="step_1",
            action="Check calendar availability for dev01",
            tool_name="check_calendar_availability",
            tool_args={"user_id": "dev01", "date": "2026-10-27"},
            depends_on=[],
        ),
        PlanStep(
            step_id="step_2",
            action="Create review task",
            tool_name="create_task",
            tool_args={"title": "Payments Review", "assignee": "dev01"},
            depends_on=["step_1"],
        ),
        PlanStep(
            step_id="step_3",
            action="Notify PM about task creation",
            tool_name="send_notification",
            tool_args={"recipient": "pm01", "message": "Payments review created"},
            depends_on=["step_2"],
        ),
        PlanStep(
            step_id="step_4",
            action="Search SOPs for follow-up",
            tool_name="search_workflow_templates",
            tool_args={"query": "review procedures"},
            depends_on=["step_3"],
        ),
    ]

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = ExecutionPlan(
        goal="Schedule review, create task, notify PM",
        steps=plan_steps,
    )

    mock_retriever = MagicMock(return_value=[{"section_title": "Review procedures"}])

    graph = create_workflow_graph(
        llm=mock_llm,
        retriever_fn=mock_retriever,
        jira_service_instance=isolated_services["jira"],
        notification_service_instance=isolated_services["notif"],
        calendar_service_instance=isolated_services["cal"],
    )

    result = graph.invoke({"user_request": "Schedule review, create task, notify PM"})

    assert result["completed_steps"] == ["step_1", "step_2", "step_3", "step_4"]
    assert result["pending_steps"] == []
    assert "step_1" in result["step_results"]
    assert result["step_results"]["step_1"]["status"] == "success"
    assert all(step.status == "completed" for step in result["plan"])
