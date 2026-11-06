from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.nodes.generate_structured_plan import generate_structured_plan
from app.agents.nodes.parse_goal import parse_goal
from app.agents.nodes.retrieve_sops import retrieve_sops
from app.schemas.state import WorkflowState

_compiled_graph: CompiledStateGraph[WorkflowState, Any, Any, Any] | None = None


def create_workflow_graph(
    checkpointer: BaseCheckpointSaver[Any],
) -> CompiledStateGraph[WorkflowState, Any, Any, Any]:
    """Create the langgraph for the workflow"""
    workflow = StateGraph(WorkflowState)
    workflow.add_node("parse_goal", parse_goal)
    workflow.add_node("retrieve_sops", retrieve_sops)
    workflow.add_node("generate_structured_plan", generate_structured_plan)

    workflow.add_edge(START, "parse_goal")
    workflow.add_edge("parse_goal", "retrieve_sops")
    workflow.add_edge("retrieve_sops", "generate_structured_plan")
    workflow.add_edge("generate_structured_plan", END)

    return workflow.compile(checkpointer=checkpointer)


def get_workflow_graph(
    checkpointer: BaseCheckpointSaver[Any],
) -> CompiledStateGraph[WorkflowState, Any, Any, Any]:
    """Return cached compiled workflow graph, reusing if checkpointer is unchanged."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = create_workflow_graph(checkpointer)
    return _compiled_graph
