from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from app.agents.nodes.parse_goal import parse_goal
from app.schemas.state import WorkflowState

def create_workflow_graph(checkpointer: BaseCheckpointSaver[Any]):
    """Create the langgraph for the workflow"""

    workflow = StateGraph(WorkflowState)
    workflow.add_node("parse_goal", parse_goal)

    workflow.add_edge(START, "parse_goal")
    workflow.add_edge("parse_goal", END)

    return workflow.compile(checkpointer=checkpointer)