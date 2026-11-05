import pytest
from langgraph.checkpoint.memory import MemorySaver

from app.agents.workflow_agent import create_workflow_graph, get_workflow_graph


@pytest.mark.asyncio
async def test_workflow_graph_execution():
    checkpointer = MemorySaver()
    graph = create_workflow_graph(checkpointer)

    result = await graph.ainvoke(
        {"user_request": "  Generate report  ", "thread_id": "t1"},
        config={"configurable": {"thread_id": "t1"}},
    )
    assert result["parsed_goal"] == "Generate report"


def test_get_workflow_graph_caching():
    checkpointer = MemorySaver()
    graph1 = get_workflow_graph(checkpointer)
    graph2 = get_workflow_graph(checkpointer)
    assert graph1 is graph2
