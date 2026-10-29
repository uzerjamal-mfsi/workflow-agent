from unittest.mock import MagicMock, patch

import pytest

from app.agents.workflow_agent import (
    TARGET_TOOLS,
    create_workflow_graph,
    generate_plan,
    parse_goal,
    workflow_graph,
)
from app.schemas.workflow import AgentState, ExecutionPlan, PlanStep

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
                tool_args={"title": "Approve Overdue Tasks"},
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
