from unittest.mock import MagicMock, patch

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END

from app.agents.workflow_agent import (
    create_workflow_graph,
    get_workflow_graph,
    route_after_approval,
    route_after_intent,
    route_after_parse_goal,
    route_after_verification,
)
from app.schemas.state import IntentClassification, Plan, Step, WorkflowState


def test_route_after_parse_goal_when_supported():
    state: WorkflowState = {"is_supported": True}
    assert route_after_parse_goal(state) == "retrieve_sops"
    assert route_after_intent(state) == "retrieve_sops"


def test_route_after_parse_goal_when_unsupported():
    state: WorkflowState = {"is_supported": False}
    assert route_after_parse_goal(state) == END
    assert route_after_intent(state) == END


def test_route_after_parse_goal_when_missing_or_none():
    assert route_after_parse_goal({}) == END
    assert route_after_parse_goal({"is_supported": None}) == END


def test_route_after_approval_when_approved():
    state: WorkflowState = {"approved": True}
    assert route_after_approval(state) == "execute_next_tool"


def test_route_after_approval_when_not_approved():
    state: WorkflowState = {"approved": False}
    assert route_after_approval(state) == END


def test_route_after_approval_when_missing_or_none():
    assert route_after_approval({}) == END
    assert route_after_approval({"approved": None}) == END


@pytest.mark.parametrize(
    "outcome,expected_destination",
    [
        ("next_step", "execute_next_tool"),
        ("retry", "execute_next_tool"),
        ("replan", "generate_structured_plan"),
        ("completed", END),
        ("escalate", END),
        (None, END),
        ("unknown_outcome", END),
    ],
)
def test_route_after_verification(outcome, expected_destination):
    state: WorkflowState = (
        {"verification_outcome": outcome} if outcome is not None else {}
    )
    assert route_after_verification(state) == expected_destination


@pytest.mark.asyncio
async def test_workflow_graph_contains_verify_node():
    checkpointer = MemorySaver()
    graph = create_workflow_graph(checkpointer)
    assert "verify" in graph.nodes


@pytest.mark.asyncio
async def test_workflow_graph_unsupported_goal_terminates_at_end():
    """Unsupported goal should stop at END after parse_goal without executing retrieve_sops."""
    checkpointer = MemorySaver()
    graph = create_workflow_graph(checkpointer)

    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = IntentClassification(
        is_supported=False,
        rejection_reason="Chit-chat is not supported.",
    )
    mock_llm.with_structured_output.return_value = mock_structured

    with patch("app.agents.nodes.parse_goal.get_llm", return_value=mock_llm):
        result = await graph.ainvoke(
            {"user_request": "How is the weather today?", "thread_id": "t_unsupported"},
            config={"configurable": {"thread_id": "t_unsupported"}},
        )

        assert result["parsed_goal"] == "How is the weather today?"
        assert result["is_supported"] is False
        assert result["rejection_reason"] == "Chit-chat is not supported."
        # SOP retrieval and planning should NOT have run
        assert "retrieved_sops" not in result
        assert result.get("plan") is None
        # Response message should be present
        assert len(result["messages"]) >= 1
        assert result["messages"][-1].content == "Chit-chat is not supported."


@pytest.mark.asyncio
async def test_workflow_graph_execution():
    checkpointer = MemorySaver()
    graph = create_workflow_graph(checkpointer)

    mock_parse_llm = MagicMock()
    mock_parse_struct = MagicMock()
    mock_parse_struct.invoke.return_value = IntentClassification(is_supported=True)
    mock_parse_llm.with_structured_output.return_value = mock_parse_struct

    mock_plan_llm = MagicMock()
    mock_plan_struct = MagicMock()
    mock_plan_struct.invoke.return_value = Plan(
        reasoning="Test plan",
        steps=[
            Step(
                step_id="step_1",
                title="Search templates",
                tool="search_workflow_templates",
                args={"query": "test"},
            )
        ],
    )
    mock_plan_llm.with_structured_output.return_value = mock_plan_struct

    with (
        patch("app.agents.nodes.parse_goal.get_llm", return_value=mock_parse_llm),
        patch("app.agents.nodes.retrieve_sops.get_qdrant_repository"),
        patch("app.agents.nodes.retrieve_sops.get_embedding_provider"),
        patch(
            "app.agents.nodes.retrieve_sops.search_sops",
            return_value=["Standard Report SOP"],
        ),
        patch(
            "app.agents.nodes.generate_structured_plan.get_llm",
            return_value=mock_plan_llm,
        ),
    ):
        result = await graph.ainvoke(
            {"user_request": "  Generate report  ", "thread_id": "t1"},
            config={"configurable": {"thread_id": "t1"}},
        )
        assert result["parsed_goal"] == "Generate report"
        assert result["is_supported"] is True
        assert "retrieved_sops" in result
        assert isinstance(result["retrieved_sops"], list)


def test_get_workflow_graph_caching():
    checkpointer = MemorySaver()
    graph1 = get_workflow_graph(checkpointer)
    graph2 = get_workflow_graph(checkpointer)
    assert graph1 is graph2
