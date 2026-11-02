import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.agents.workflow_agent import (
    TARGET_TOOLS,
    create_workflow_graph,
    escalate,
    execute_next_tool,
    generate_idempotency_key,
    generate_plan,
    parse_goal,
    validate_dependencies,
    verify_step,
    workflow_graph,
)
from app.exceptions.domain import TransientError
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

    assert result["completed_steps"] == ["step_1", "step_2", "step_3", "step_4"]
    assert result["pending_steps"] == []
    assert result["failed_steps"] == []
    assert "step_1" in result["step_results"]
    assert all(step.status == "completed" for step in result["plan"])


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


def test_workflow_graph_dependent_plan_execution():
    """Verify 4-step dependent plan executes strictly in dependency order and loops until completion."""
    call_order = []

    def mock_jira_create(title, assignee="dev01", priority="Medium", **kwargs):
        call_order.append("step_2")
        return {"task_id": "TASK-201", "title": title}

    def mock_jira_update(task_id, fields=None, **kwargs):
        call_order.append("step_3")
        return {"task_id": task_id, "status": "In Progress"}

    def mock_notif_send(recipient, message, **kwargs):
        call_order.append("step_4")
        return {"status": "sent", "recipient": recipient}

    def mock_cal_check(user_id, date="2026-10-27", **kwargs):
        call_order.append("step_1")
        return {"status": "success", "user_id": user_id, "available": True}

    mock_jira = MagicMock()
    mock_jira.create_task.side_effect = mock_jira_create
    mock_jira.update_task.side_effect = mock_jira_update
    mock_notif = MagicMock()
    mock_notif.send_notification.side_effect = mock_notif_send
    mock_cal = MagicMock()
    mock_cal.check_calendar_availability.side_effect = mock_cal_check

    # Deliberately unordered steps to ensure execution order is driven strictly by dependencies
    plan = ExecutionPlan(
        goal="Execute dependent pipeline",
        steps=[
            PlanStep(
                step_id="step_4",
                action="Notify PM",
                tool_name="send_notification",
                tool_args={"recipient": "pm01", "message": "Done"},
                depends_on=["step_3"],
            ),
            PlanStep(
                step_id="step_2",
                action="Create task",
                tool_name="create_task",
                tool_args={"title": "Setup job", "assignee": "dev01"},
                depends_on=["step_1"],
            ),
            PlanStep(
                step_id="step_1",
                action="Check calendar",
                tool_name="check_calendar_availability",
                tool_args={"user_id": "dev01", "date": "2026-10-27"},
                depends_on=[],
            ),
            PlanStep(
                step_id="step_3",
                action="Update task",
                tool_name="update_task",
                tool_args={"task_id": "step_2", "fields": {"status": "In Progress"}},
                depends_on=["step_2"],
            ),
        ],
    )

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = plan

    graph = create_workflow_graph(
        llm=mock_llm,
        jira_service_instance=mock_jira,
        notification_service_instance=mock_notif,
        calendar_service_instance=mock_cal,
    )
    result = graph.invoke({"user_request": "Execute dependent pipeline"})

    assert call_order == ["step_1", "step_2", "step_3", "step_4"]
    assert result["completed_steps"] == ["step_1", "step_2", "step_3", "step_4"]
    assert result["pending_steps"] == []
    assert result["failed_steps"] == []
    assert all(s.status == "completed" for s in result["plan"])


def test_validate_dependencies_selects_first_satisfied_step():
    """Verify validate_dependencies selects the first step with satisfied dependencies."""
    steps = [
        PlanStep(step_id="step_2", action="Step 2", tool_name="create_task", depends_on=["step_1"]),
        PlanStep(step_id="step_1", action="Step 1", tool_name="check_calendar_availability", depends_on=[]),
    ]
    state: AgentState = {
        "plan": steps,
        "pending_steps": ["step_2", "step_1"],
        "completed_steps": [],
        "failed_steps": [],
        "step_results": {},
    }
    result = validate_dependencies(state)
    assert result["current_step_id"] == "step_1"


def test_validate_dependencies_cascades_failed_dependency():
    """Verify validate_dependencies marks dependent steps as failed when parent step failed."""
    steps = [
        PlanStep(step_id="step_1", action="Step 1", tool_name="check_calendar_availability", status="failed"),
        PlanStep(step_id="step_2", action="Step 2", tool_name="create_task", depends_on=["step_1"]),
        PlanStep(step_id="step_3", action="Step 3", tool_name="update_task", depends_on=["step_2"]),
    ]
    state: AgentState = {
        "plan": steps,
        "pending_steps": ["step_2", "step_3"],
        "completed_steps": [],
        "failed_steps": ["step_1"],
        "step_results": {"step_1": {"status": "failed", "error": "Calendar service unreachable"}},
    }
    result = validate_dependencies(state)
    assert result["pending_steps"] == []
    assert "step_2" in result["failed_steps"]
    assert "step_3" in result["failed_steps"]
    assert steps[1].status == "failed"
    assert steps[2].status == "failed"


def test_validate_dependencies_permission_check():
    """Verify validate_dependencies fails steps when user lacks required permission."""
    step = PlanStep(
        step_id="step_1",
        action="Create task with QA user",
        tool_name="create_task",
        tool_args={"assignee": "qa01", "title": "QA Test"},
        depends_on=[],
    )
    state: AgentState = {
        "plan": [step],
        "pending_steps": ["step_1"],
        "completed_steps": [],
        "failed_steps": [],
        "step_results": {},
    }
    result = validate_dependencies(state)
    assert "step_1" in result["failed_steps"]
    assert result["step_results"]["step_1"]["status"] == "failed"
    assert "permission" in result["step_results"]["step_1"]["error"].lower()


def test_workflow_graph_failure_escalates():
    """Verify workflow graph routes to escalate node when a tool fails."""
    plan = ExecutionPlan(
        goal="Run failing step",
        steps=[
            PlanStep(
                step_id="step_fail",
                action="Fail step",
                tool_name="create_task",
                tool_args={"assignee": "qa01", "title": "Unauthorized"},
                depends_on=[],
            ),
        ],
    )
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = plan

    graph = create_workflow_graph(llm=mock_llm)
    result = graph.invoke({"user_request": "Run failing step"})

    assert result.get("escalated") is True
    assert "step_fail" in result["failed_steps"]


def test_transient_failure_retries_and_succeeds():
    """Verify transient tool failure retries up to 2 times and succeeds."""
    mock_jira = MagicMock()
    mock_jira.create_task.side_effect = [
        TransientError("Temporary timeout"),
        TimeoutError("Connection timed out"),
        {"task_id": "TASK-777", "title": "API Review"},
    ]

    step = PlanStep(
        step_id="step_retry",
        action="Create API review task",
        tool_name="create_task",
        tool_args={"title": "API Review", "assignee": "dev01"},
        depends_on=[],
    )
    plan = ExecutionPlan(goal="Test retry", steps=[step])
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = plan

    graph = create_workflow_graph(llm=mock_llm, jira_service_instance=mock_jira)
    result = graph.invoke({"user_request": "Test retry"})

    assert mock_jira.create_task.call_count == 3
    assert result["completed_steps"] == ["step_retry"]
    assert result["failed_steps"] == []
    assert result["plan"][0].status == "completed"
    assert result["plan"][0].retry_count == 2


def test_transient_failure_exceeds_max_retries_and_escalates():
    """Verify transient failures reaching max retries mark step as failed and escalate."""
    mock_jira = MagicMock()
    mock_jira.create_task.side_effect = [
        TransientError("Temporary timeout 1"),
        TransientError("Temporary timeout 2"),
        TransientError("Temporary timeout 3"),
    ]

    step = PlanStep(
        step_id="step_fail_retry",
        action="Create API review task",
        tool_name="create_task",
        tool_args={"title": "API Review", "assignee": "dev01"},
        depends_on=[],
    )
    plan = ExecutionPlan(goal="Test retry max", steps=[step])
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = plan

    graph = create_workflow_graph(llm=mock_llm, jira_service_instance=mock_jira)
    result = graph.invoke({"user_request": "Test retry max"})

    assert mock_jira.create_task.call_count == 3
    assert result.get("escalated") is True
    assert "step_fail_retry" in result["failed_steps"]
    assert result["plan"][0].status == "failed"
    assert result["plan"][0].retry_count == 2


def test_non_transient_failure_does_not_retry():
    """Verify non-transient error fails immediately without retrying."""
    mock_jira = MagicMock()
    mock_jira.create_task.side_effect = ValueError("Invalid assignee")

    step = PlanStep(
        step_id="step_bad_arg",
        action="Create task",
        tool_name="create_task",
        tool_args={"title": "Bad task", "assignee": "dev01"},
        depends_on=[],
    )
    plan = ExecutionPlan(goal="Test permanent failure", steps=[step])
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = plan

    graph = create_workflow_graph(llm=mock_llm, jira_service_instance=mock_jira)
    result = graph.invoke({"user_request": "Test permanent failure"})

    assert mock_jira.create_task.call_count == 1
    assert result.get("escalated") is True
    assert "step_bad_arg" in result["failed_steps"]
    assert result["plan"][0].status == "failed"
    assert result["plan"][0].retry_count == 0


def test_idempotency_prevents_duplicate_jira_task(tmp_path: Path):
    """Verify re-running a step with same idempotency key returns cached Jira task."""
    temp_tasks = tmp_path / "tasks.json"
    temp_team = tmp_path / "team_directory.json"
    shutil.copyfile(DEFAULT_TASKS, temp_tasks)
    shutil.copyfile(DEFAULT_TEAM, temp_team)
    jira = JiraService(tasks_path=temp_tasks, team_path=temp_team)

    step = PlanStep(
        step_id="step_create",
        action="Create review task",
        tool_name="create_task",
        tool_args={"title": "Unique Review Task", "assignee": "dev01"},
    )
    state: AgentState = {
        "plan": [step],
        "current_step_id": "step_create",
        "pending_steps": ["step_create"],
        "completed_steps": [],
        "failed_steps": [],
        "step_results": {},
        "executed_keys": {},
    }

    res1 = execute_next_tool(state, jira_service_instance=jira)
    task_id1 = res1["step_results"]["step_create"]["task_id"]
    assert len(res1["executed_keys"]) == 1

    state["executed_keys"] = res1["executed_keys"]
    res2 = execute_next_tool(state, jira_service_instance=jira)
    task_id2 = res2["step_results"]["step_create"]["task_id"]

    assert task_id1 == task_id2
    matching = [t for t in jira.list_tasks() if t.get("title") == "Unique Review Task"]
    assert len(matching) == 1


def test_idempotency_prevents_duplicate_notification():
    """Verify re-running a step with same idempotency key returns cached notification result."""
    mock_notif = MagicMock()
    mock_notif.send_notification.return_value = {
        "status": "sent",
        "recipient": "dev01",
        "message": "Review ready",
    }

    step = PlanStep(
        step_id="step_notify",
        action="Send notification",
        tool_name="send_notification",
        tool_args={"recipient": "dev01", "message": "Review ready"},
    )
    state: AgentState = {
        "plan": [step],
        "current_step_id": "step_notify",
        "pending_steps": ["step_notify"],
        "completed_steps": [],
        "failed_steps": [],
        "step_results": {},
        "executed_keys": {},
    }

    res1 = execute_next_tool(state, notification_service_instance=mock_notif)
    assert mock_notif.send_notification.call_count == 1
    assert len(res1["executed_keys"]) == 1

    state["executed_keys"] = res1["executed_keys"]
    res2 = execute_next_tool(state, notification_service_instance=mock_notif)
    assert mock_notif.send_notification.call_count == 1
    assert res1["step_results"]["step_notify"] == res2["step_results"]["step_notify"]


def test_idempotency_key_deterministic_with_differently_ordered_args():
    """Verify idempotency key produces identical hash regardless of dict key ordering."""
    key1 = generate_idempotency_key("step_1", "create_task", {"title": "A", "priority": "High"})
    key2 = generate_idempotency_key("step_1", "create_task", {"priority": "High", "title": "A"})
    assert key1 == key2
