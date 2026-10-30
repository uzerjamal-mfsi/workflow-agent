import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.agents.workflow_agent import (
    TARGET_TOOLS,
    create_workflow_graph,
    execute_next_tool,
    generate_plan,
    parse_goal,
    verify_step,
    workflow_graph,
)
from app.schemas.workflow import AgentState, ExecutionPlan, PlanStep
from app.services.jira_service import (
    DEFAULT_TASKS,
    DEFAULT_TEAM,
    JiraService,
)
from app.tools.jira_tools import (
    create_task_tool,
    list_tasks_tool,
    update_task_tool,
)

EXAMPLE_REQUESTS = [
    "Create an API review task, assign it to dev01 and notify pm01",
    "Update all overdue high-priority tasks after approval",
]


def _mock_plan_for_request(request: str) -> ExecutionPlan:
    if "API review" in request:
        return ExecutionPlan(
            goal="Create an API review task, assign it to dev01 and notify pm01",
            steps=[
                PlanStep(
                    step_id="step_1",
                    action="Check calendar availability for dev01",
                    tool_name="check_calendar_availability",
                    tool_args={"user_id": "dev01"},
                    depends_on=[],
                ),
                PlanStep(
                    step_id="step_2",
                    action="Create API review task",
                    tool_name="create_task",
                    tool_args={"title": "API Review", "assignee": "dev01"},
                    depends_on=["step_1"],
                ),
                PlanStep(
                    step_id="step_3",
                    action="Update task with review guidelines",
                    tool_name="update_task",
                    tool_args={"task_id": "step_2", "priority": "high"},
                    depends_on=["step_2"],
                ),
                PlanStep(
                    step_id="step_4",
                    action="Notify pm01 about task assignment",
                    tool_name="send_notification",
                    tool_args={"recipient": "pm01", "message": "Review ready"},
                    depends_on=["step_3"],
                ),
            ],
        )

    return ExecutionPlan(
        goal="Update all overdue high-priority tasks after approval",
        steps=[
            PlanStep(
                step_id="step_1",
                action="Check calendar availability for approval sync",
                tool_name="check_calendar_availability",
                tool_args={"team": "leads"},
                depends_on=[],
            ),
            PlanStep(
                step_id="step_2",
                action="Create approval task tracking item",
                tool_name="create_task",
                tool_args={"title": "Approve Overdue Tasks", "assignee": "pm01"},
                depends_on=["step_1"],
            ),
            PlanStep(
                step_id="step_3",
                action="Update overdue high-priority tasks status",
                tool_name="update_task",
                tool_args={"filter": "overdue_high_priority", "status": "approved"},
                depends_on=["step_2"],
            ),
            PlanStep(
                step_id="step_4",
                action="Send notification about updated tasks",
                tool_name="send_notification",
                tool_args={"channel": "task-updates", "message": "Tasks updated"},
                depends_on=["step_3"],
            ),
        ],
    )


def test_parse_goal_node():
    """Verify parse_goal extracts the goal from user_request."""
    state: AgentState = {"user_request": "  Create an API review task  "}
    result = parse_goal(state)
    assert result == {"parsed_goal": "Create an API review task"}


def test_generate_plan_node():
    """Verify generate_plan returns plan steps from structured LLM output."""
    mock_llm = MagicMock()
    expected_plan = _mock_plan_for_request(EXAMPLE_REQUESTS[0])
    mock_llm.with_structured_output.return_value.invoke.return_value = expected_plan

    state: AgentState = {"parsed_goal": EXAMPLE_REQUESTS[0]}
    result = generate_plan(state, llm=mock_llm)

    assert "plan" in result
    assert len(result["plan"]) >= 4
    assert result["plan"] == expected_plan.steps
    assert result["pending_steps"] == [s.step_id for s in expected_plan.steps]
    assert result["completed_steps"] == []


@pytest.mark.parametrize("user_request", EXAMPLE_REQUESTS)
def test_workflow_graph_execution(user_request: str):
    """Verify workflow graph generates a structured plan with 4+ steps."""
    mock_llm = MagicMock()
    expected_plan = _mock_plan_for_request(user_request)
    mock_llm.with_structured_output.return_value.invoke.return_value = expected_plan

    graph = create_workflow_graph(llm=mock_llm)
    result = graph.invoke({"user_request": user_request})

    assert result["parsed_goal"] == user_request
    assert "plan" in result

    steps = result["plan"]
    assert len(steps) >= 4
    for step in steps:
        assert isinstance(step, PlanStep)
        assert step.step_id
        assert step.action
        assert step.tool_name in TARGET_TOOLS


@pytest.mark.parametrize("user_request", EXAMPLE_REQUESTS)
def test_default_workflow_graph_with_mocked_client(user_request: str):
    """Verify the pre-compiled workflow_graph works when default LLM is patched."""
    mock_client = MagicMock()
    expected_plan = _mock_plan_for_request(user_request)
    mock_client.with_structured_output.return_value.invoke.return_value = expected_plan

    with patch(
        "app.agents.workflow_agent.get_default_chat_client", return_value=mock_client
    ):
        result = workflow_graph.invoke({"user_request": user_request})

    assert result["parsed_goal"] == user_request
    assert len(result["plan"]) >= 4
    assert all(step.tool_name in TARGET_TOOLS for step in result["plan"])


def test_execute_next_tool_noop_stub():
    """Verify unbuilt tools are logged as no-op stubs."""
    step = PlanStep(
        step_id="step_1",
        action="Check calendar",
        tool_name="check_calendar_availability",
    )
    state: AgentState = {
        "plan": [step],
        "pending_steps": ["step_1"],
        "completed_steps": [],
        "failed_steps": [],
        "step_results": {},
    }

    result = execute_next_tool(state)
    assert result["current_step_id"] == "step_1"
    assert result["step_results"]["step_1"]["status"] == "skipped"


def test_execute_next_tool_jira_create(tmp_path: Path):
    """Verify execute_next_tool creates a Jira task."""
    temp_tasks = tmp_path / "tasks.json"
    temp_team = tmp_path / "team_directory.json"
    shutil.copyfile(DEFAULT_TASKS, temp_tasks)
    shutil.copyfile(DEFAULT_TEAM, temp_team)
    isolated_jira = JiraService(tasks_path=temp_tasks, team_path=temp_team)

    step = PlanStep(
        step_id="step_2",
        action="Create review task",
        tool_name="create_task",
        tool_args={"title": "Test review", "assignee": "dev01"},
    )
    state: AgentState = {
        "plan": [step],
        "pending_steps": ["step_2"],
        "completed_steps": [],
        "failed_steps": [],
        "step_results": {},
    }

    result = execute_next_tool(state, jira_service_instance=isolated_jira)
    assert result["current_step_id"] == "step_2"
    assert "task_id" in result["step_results"]["step_2"]
    assert result["step_results"]["step_2"]["title"] == "Test review"


def test_verify_step_success():
    """Verify verify_step moves successful step from pending to completed."""
    step = PlanStep(
        step_id="step_1",
        action="Check calendar",
        tool_name="check_calendar_availability",
    )
    state: AgentState = {
        "plan": [step],
        "current_step_id": "step_1",
        "pending_steps": ["step_1", "step_2"],
        "completed_steps": [],
        "failed_steps": [],
        "step_results": {"step_1": {"status": "skipped"}},
    }

    res = verify_step(state)
    assert res["completed_steps"] == ["step_1"]
    assert res["pending_steps"] == ["step_2"]
    assert res["failed_steps"] == []
    assert step.status == "completed"


def test_verify_step_failure():
    """Verify verify_step moves failed step from pending to failed."""
    step = PlanStep(
        step_id="step_1",
        action="Check calendar",
        tool_name="check_calendar_availability",
    )
    state: AgentState = {
        "plan": [step],
        "current_step_id": "step_1",
        "pending_steps": ["step_1", "step_2"],
        "completed_steps": [],
        "failed_steps": [],
        "step_results": {"step_1": {"status": "failed", "error": "Connection error"}},
    }

    res = verify_step(state)
    assert res["failed_steps"] == ["step_1"]
    assert res["pending_steps"] == ["step_2"]
    assert res["completed_steps"] == []
    assert step.status == "failed"


def test_workflow_graph_tool_execution_updates_state(tmp_path: Path):
    """Verify wired graph updates state after executing the next tool."""
    temp_tasks = tmp_path / "tasks.json"
    temp_team = tmp_path / "team_directory.json"
    shutil.copyfile(DEFAULT_TASKS, temp_tasks)
    shutil.copyfile(DEFAULT_TEAM, temp_team)
    isolated_jira = JiraService(tasks_path=temp_tasks, team_path=temp_team)

    mock_llm = MagicMock()
    expected_plan = _mock_plan_for_request(EXAMPLE_REQUESTS[0])
    mock_llm.with_structured_output.return_value.invoke.return_value = expected_plan

    graph = create_workflow_graph(llm=mock_llm, jira_service_instance=isolated_jira)
    result = graph.invoke({"user_request": EXAMPLE_REQUESTS[0]})

    # First step in plan is check_calendar_availability (stub)
    assert result["current_step_id"] == "step_1"
    assert result["completed_steps"] == ["step_1"]
    assert result["pending_steps"] == ["step_2", "step_3", "step_4"]
    assert result["failed_steps"] == []
    assert "step_1" in result["step_results"]
    assert result["plan"][0].status == "completed"
    assert result["plan"][1].status == "pending"


def test_jira_langchain_tools_execution(tmp_path: Path):
    """Verify LangChain tool wrappers can be invoked directly."""
    temp_tasks = tmp_path / "tasks.json"
    temp_team = tmp_path / "team_directory.json"
    shutil.copyfile(DEFAULT_TASKS, temp_tasks)
    shutil.copyfile(DEFAULT_TEAM, temp_team)
    isolated = JiraService(tasks_path=temp_tasks, team_path=temp_team)

    with (
        patch("app.tools.jira_tools.create_task", side_effect=isolated.create_task),
        patch("app.tools.jira_tools.update_task", side_effect=isolated.update_task),
        patch("app.tools.jira_tools.list_tasks", side_effect=isolated.list_tasks),
    ):
        created = create_task_tool.invoke(
            {"title": "Tool test task", "assignee": "dev01", "priority": "Low"}
        )
        assert "task_id" in created
        assert created["title"] == "Tool test task"

        updated = update_task_tool.invoke(
            {"task_id": created["task_id"], "fields": {"status": "In Progress"}}
        )
        assert updated["status"] == "In Progress"

        tasks = list_tasks_tool.invoke({"task_id": created["task_id"]})
        assert len(tasks) == 1
