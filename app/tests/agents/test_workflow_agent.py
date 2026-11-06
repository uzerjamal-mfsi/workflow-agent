import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END

from app.agents.workflow_agent import (
    create_workflow_graph,
    get_workflow_graph,
    route_after_approval,
    route_after_verification,
)
from app.schemas.state import WorkflowState


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
    state: WorkflowState = {"verification_outcome": outcome} if outcome is not None else {}
    assert route_after_verification(state) == expected_destination


@pytest.mark.asyncio
async def test_workflow_graph_contains_verify_node():
    checkpointer = MemorySaver()
    graph = create_workflow_graph(checkpointer)
    assert "verify" in graph.nodes


@pytest.mark.asyncio
async def test_workflow_graph_execution():
    checkpointer = MemorySaver()
    graph = create_workflow_graph(checkpointer)

    result = await graph.ainvoke(
        {"user_request": "  Generate report  ", "thread_id": "t1"},
        config={"configurable": {"thread_id": "t1"}},
    )
    assert result["parsed_goal"] == "Generate report"
    assert "retrieved_sops" in result
    assert isinstance(result["retrieved_sops"], list)


def test_get_workflow_graph_caching():
    checkpointer = MemorySaver()
    graph1 = get_workflow_graph(checkpointer)
    graph2 = get_workflow_graph(checkpointer)
    assert graph1 is graph2
