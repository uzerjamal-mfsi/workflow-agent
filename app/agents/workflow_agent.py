from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.nodes.approval_gate import approval_gate
from app.agents.nodes.execute_new_tool import execute_next_tool
from app.agents.nodes.generate_structured_plan import generate_structured_plan
from app.agents.nodes.parse_goal import parse_goal
from app.agents.nodes.retrieve_sops import retrieve_sops
from app.agents.nodes.validate_dependencies_and_permissions import validate_dependencies_and_permission
from app.agents.nodes.verify import verify
from app.schemas.state import WorkflowState

_compiled_graph: CompiledStateGraph[WorkflowState, Any, Any, Any] | None = None

def route_after_approval(state: WorkflowState) -> str:
    """Route to execution if approved, otherwise stop."""
    if state.get("approved", False):
        return "execute_next_tool"
    return END

def route_after_verification(state: WorkflowState) -> str:
    """Decides whether to execute next step, retry, replan, or end."""
    outcome = state.get("verification_outcome")
    match outcome:
        case "next_step" | "retry":
            return "execute_next_tool"
        case "replan":
            return "generate_structured_plan"
        case _:
            return END

def create_workflow_graph(
    checkpointer: BaseCheckpointSaver[Any],
) -> CompiledStateGraph[WorkflowState, Any, Any, Any]:
    """Create the langgraph for the workflow"""
    workflow = StateGraph(WorkflowState)
    workflow.add_node("parse_goal", parse_goal)
    workflow.add_node("retrieve_sops", retrieve_sops)
    workflow.add_node("generate_structured_plan", generate_structured_plan)
    workflow.add_node("validate_dependencies_and_permissions", validate_dependencies_and_permission)
    workflow.add_node("approval_gate", approval_gate)
    workflow.add_node("execute_next_tool", execute_next_tool)
    workflow.add_node("verify", verify)

    # --- Edges ---
    workflow.add_edge(START, "parse_goal")
    workflow.add_edge("parse_goal", "retrieve_sops")
    workflow.add_edge("retrieve_sops", "generate_structured_plan")
    workflow.add_edge("generate_structured_plan", "validate_dependencies_and_permissions")
    workflow.add_edge("validate_dependencies_and_permissions", "approval_gate")
    workflow.add_conditional_edges(
        "approval_gate",
        route_after_approval,
        {
            "execute_next_tool": "execute_next_tool",
            "generate_structured_plan": "generate_structured_plan",
            END: END,
        },
    )
    workflow.add_edge("execute_next_tool", "verify")
    workflow.add_conditional_edges(
        "verify",
        route_after_verification,
        {
            "execute_next_tool": "execute_next_tool",
            "generate_structured_plan": "generate_structured_plan",
            END: END,
        },
    )

    return workflow.compile(checkpointer=checkpointer)


def get_workflow_graph(
    checkpointer: BaseCheckpointSaver[Any],
) -> CompiledStateGraph[WorkflowState, Any, Any, Any]:
    """Return cached compiled workflow graph, reusing if checkpointer is unchanged."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = create_workflow_graph(checkpointer)
    return _compiled_graph
