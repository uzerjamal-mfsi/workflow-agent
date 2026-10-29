from typing import Any

from langgraph.graph import END, START, StateGraph
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from app.llms.llm_factory import get_default_chat_client
from app.prompts.planner_prompt import (
    PLANNER_SYSTEM_PROMPT,
    PLANNER_USER_PROMPT,
    PLANNER_USER_PROMPT_WITH_SOPS,
)
from app.schemas.workflow import AgentState, ExecutionPlan
from app.services.core_services.sop_service import search_workflow_templates

TARGET_TOOLS = (
    "check_calendar_availability",
    "create_task",
    "update_task",
    "send_notification",
)


def parse_goal(state: AgentState) -> dict[str, Any]:
    """Extract a concise goal string from the user request."""
    return {"parsed_goal": state.get("user_request", "").strip()}


def retrieve_sops(state: AgentState, search_fn=None) -> dict[str, Any]:
    """Retrieve relevant SOP sections for the workflow goal."""
    if state.get("retrieved_sops"):
        return {"retrieved_sops": state["retrieved_sops"]}

    goal = state.get("parsed_goal") or state.get("user_request", "")
    if not goal:
        return {"retrieved_sops": []}

    fn = search_fn or search_workflow_templates
    try:
        sops = fn(goal)
    except (ConnectionError, ResponseHandlingException, UnexpectedResponse):
        sops = []
    return {"retrieved_sops": sops}


def generate_plan(state: AgentState, llm=None) -> dict[str, Any]:
    """Generate an ordered plan of 4+ steps using structured LLM output."""
    client = llm or get_default_chat_client()
    planner = client.with_structured_output(ExecutionPlan)
    goal = state.get("parsed_goal") or state.get("user_request", "")
    sops = state.get("retrieved_sops", [])

    if sops:
        sop_lines = [
            sop.get("content") or sop.get("page_content") or ""
            for sop in sops
            if sop.get("content") or sop.get("page_content")
        ]
        sop_text = "\n\n".join(sop_lines)
        user_message = PLANNER_USER_PROMPT_WITH_SOPS.format(goal=goal, sops=sop_text)
    else:
        user_message = PLANNER_USER_PROMPT.format(goal=goal)

    messages = [
        ("system", PLANNER_SYSTEM_PROMPT),
        ("user", user_message),
    ]
    plan = planner.invoke(messages)
    steps = plan.steps if isinstance(plan, ExecutionPlan) else plan.get("steps", [])
    return {"plan": steps}


def create_workflow_graph(llm=None, retriever_fn=None):
    workflow = StateGraph(AgentState)
    workflow.add_node("parse_goal", parse_goal)
    workflow.add_node(
        "retrieve_sops",
        (lambda state: retrieve_sops(state, search_fn=retriever_fn))
        if retriever_fn
        else retrieve_sops,
    )
    workflow.add_node(
        "generate_plan",
        (lambda state: generate_plan(state, llm=llm)) if llm else generate_plan,
    )
    workflow.add_edge(START, "parse_goal")
    workflow.add_edge("parse_goal", "retrieve_sops")
    workflow.add_edge("retrieve_sops", "generate_plan")
    workflow.add_edge("generate_plan", END)
    return workflow.compile()


workflow_graph = create_workflow_graph()
