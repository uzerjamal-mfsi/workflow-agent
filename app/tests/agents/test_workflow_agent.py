import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END

from app.agents.workflow_agent import (
    create_workflow_graph,
    get_workflow_graph,
    route_after_approval,
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
