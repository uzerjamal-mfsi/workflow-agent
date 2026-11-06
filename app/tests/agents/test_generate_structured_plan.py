from unittest.mock import MagicMock, patch

from app.agents.nodes.generate_structured_plan import generate_structured_plan
from app.schemas.core_schemas.tool_schemas import CreateTaskArgs
from app.schemas.state import Plan, Step, WorkflowState


def test_generate_structured_plan_empty_goal():
    state: WorkflowState = {
        "parsed_goal": "",
        "retrieved_sops": ["SOP 1"],
    }
    with patch("app.agents.nodes.generate_structured_plan.get_llm") as mock_get_llm:
        result = generate_structured_plan(state)
        assert result["plan"].reasoning == "No goal provided"
        assert result["plan"].steps == []
        mock_get_llm.assert_not_called()


def test_generate_structured_plan_missing_goal():
    state: WorkflowState = {
        "retrieved_sops": ["SOP 1"],
    }
    with patch("app.agents.nodes.generate_structured_plan.get_llm") as mock_get_llm:
        result = generate_structured_plan(state)
        assert result["plan"].reasoning == "No goal provided"
        assert result["plan"].steps == []
        mock_get_llm.assert_not_called()


def test_generate_structured_plan_success():
    state: WorkflowState = {
        "parsed_goal": "Create a task for bug fix",
        "retrieved_sops": ["Follow Jira standard procedure."],
    }
    expected_plan = Plan(
        reasoning="Based on SOP, create task.",
        steps=[
            Step(
                step_id="step_1",
                title="Create task",
                tool="create_task",
                args=CreateTaskArgs(
                    title="Bug fix",
                    assignee="dev01",
                    priority="High",
                ),
            )
        ],
    )

    mock_llm = MagicMock()
    mock_structured_llm = MagicMock()
    mock_structured_llm.invoke.return_value = expected_plan
    mock_llm.with_structured_output.return_value = mock_structured_llm

    with patch(
        "app.agents.nodes.generate_structured_plan.get_llm",
        return_value=mock_llm,
    ):
        result = generate_structured_plan(state)

        assert result == {"plan": expected_plan}
        mock_llm.with_structured_output.assert_called_once_with(Plan)
        mock_structured_llm.invoke.assert_called_once()


def test_generate_structured_plan_without_sops_uses_default_context():
    state: WorkflowState = {
        "parsed_goal": "General workflow",
        "retrieved_sops": [],
    }
    expected_plan = Plan(reasoning="No SOP fallback", steps=[])

    mock_llm = MagicMock()
    mock_structured_llm = MagicMock()
    mock_structured_llm.invoke.return_value = expected_plan
    mock_llm.with_structured_output.return_value = mock_structured_llm

    with patch(
        "app.agents.nodes.generate_structured_plan.get_llm",
        return_value=mock_llm,
    ):
        result = generate_structured_plan(state)

        assert result == {"plan": expected_plan}
        called_messages = mock_structured_llm.invoke.call_args[0][0]
        assert len(called_messages) == 2
        assert "No specific SOPs retrieved." in called_messages[0].content
        assert "General workflow" in called_messages[1].content
