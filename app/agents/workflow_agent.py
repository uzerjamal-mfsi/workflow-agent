from typing import Any

from langgraph.graph import END, START, StateGraph

from app.llms.llm_factory import get_default_chat_client
from app.prompts.planner_prompt import PLANNER_SYSTEM_PROMPT, PLANNER_USER_PROMPT
from app.schemas.workflow import AgentState, ExecutionPlan

TARGET_TOOLS = (
    "check_calendar_availability",
    "create_task",
    "update_task",
    "send_notification",
)


def parse_goal(state: AgentState) -> dict[str, Any]:
    """Extract a concise goal string from the user request."""
    return {"parsed_goal": state.get("user_request", "").strip()}


def generate_plan(state: AgentState, llm=None) -> dict[str, Any]:
    """Generate an ordered plan of 4+ steps using structured LLM output."""
    client = llm or get_default_chat_client()
    planner = client.with_structured_output(ExecutionPlan)
    goal = state.get("parsed_goal") or state.get("user_request", "")

    messages = [
        ("system", PLANNER_SYSTEM_PROMPT),
        ("user", PLANNER_USER_PROMPT.format(goal=goal)),
    ]
    plan = planner.invoke(messages)
    steps = plan.steps if isinstance(plan, ExecutionPlan) else plan.get("steps", [])
    return {"plan": steps}


def create_workflow_graph(llm=None):
    workflow = StateGraph(AgentState)
    workflow.add_node("parse_goal", parse_goal)
    workflow.add_node(
        "generate_plan",
        (lambda state: generate_plan(state, llm=llm)) if llm else generate_plan,
    )
    workflow.add_edge(START, "parse_goal")
    workflow.add_edge("parse_goal", "generate_plan")
    workflow.add_edge("generate_plan", END)
    return workflow.compile()


workflow_graph = create_workflow_graph()
