import copy
import logging
from typing import Any

from langgraph.graph import END, START, StateGraph
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from app.llms.llm_factory import get_default_chat_client
from app.prompts.planner_prompt import (
    PLANNER_SYSTEM_PROMPT,
    PLANNER_USER_PROMPT,
    PLANNER_USER_PROMPT_WITH_SOPS,
)
from app.schemas.workflow import AgentState, ExecutionPlan, PlanStep
from app.services.core_services.sop_service import search_workflow_templates
from app.tools.calendar_tools import check_calendar_availability_tool
from app.tools.jira_tools import create_task_tool, update_task_tool
from app.tools.notification_tools import send_notification_tool

logger = logging.getLogger(__name__)

TARGET_TOOLS = (
    "check_calendar_availability",
    "create_task",
    "update_task",
    "send_notification",
    "search_workflow_templates",
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
    step_ids = [
        s.step_id if isinstance(s, PlanStep) else s.get("step_id", "") for s in steps
    ]
    return {
        "plan": steps,
        "pending_steps": step_ids,
        "completed_steps": [],
        "failed_steps": [],
        "step_results": {},
    }


def execute_next_tool(
    state: AgentState,
    jira_service_instance=None,
    notification_service_instance=None,
    calendar_service_instance=None,
    retriever_fn=None,
) -> dict[str, Any]:
    """Execute the next pending step from the plan."""
    plan = state.get("plan", [])
    completed = set(state.get("completed_steps", []))
    failed = set(state.get("failed_steps", []))

    pending = list(
        state.get("pending_steps")
        if state.get("pending_steps") is not None
        else [
            s.step_id if isinstance(s, PlanStep) else s["step_id"]
            for s in plan
            if (s.step_id if isinstance(s, PlanStep) else s.get("step_id"))
            not in completed
            and (s.step_id if isinstance(s, PlanStep) else s.get("step_id"))
            not in failed
        ]
    )

    if not pending:
        return {"current_step_id": None}

    step_id = pending[0]
    step = next(
        (
            s
            for s in plan
            if (s.step_id if isinstance(s, PlanStep) else s.get("step_id")) == step_id
        ),
        None,
    )
    if not step:
        return {"current_step_id": None}

    tool_name = (
        step.tool_name if isinstance(step, PlanStep) else step.get("tool_name", "")
    )
    raw_args = (
        step.tool_args if isinstance(step, PlanStep) else step.get("tool_args", {})
    )
    tool_args = copy.deepcopy(raw_args) if isinstance(raw_args, dict) else {}

    results = dict(state.get("step_results", {}))

    # Resolve task_id if it refers to a previously executed step
    raw_task_id = tool_args.get("task_id")
    if raw_task_id and raw_task_id in results:
        prev = results[raw_task_id]
        if isinstance(prev, dict):
            resolved_id = prev.get("task_id") or prev.get("task", {}).get("task_id")
            if resolved_id:
                tool_args["task_id"] = resolved_id

    try:
        if tool_name == "create_task":
            if not tool_args.get("title"):
                action = (
                    step.action
                    if isinstance(step, PlanStep)
                    else step.get("action", "")
                )
                tool_args["title"] = action or "Untitled Task"

            if jira_service_instance:
                title = tool_args.pop("title")
                assignee = tool_args.pop("assignee", "dev01")
                priority = tool_args.pop("priority", "Medium")
                res = jira_service_instance.create_task(
                    title=title, assignee=assignee, priority=priority, **tool_args
                )
            else:
                res = create_task_tool.invoke(tool_args)

        elif tool_name == "update_task":
            if jira_service_instance:
                if tool_args.get("filter") == "overdue_high_priority":
                    tool_args.pop("filter")
                    overdue = jira_service_instance.get_overdue_high_priority_tasks()
                    res = [
                        jira_service_instance.update_task(
                            task_id=t["task_id"], fields=dict(tool_args)
                        )
                        for t in overdue
                        if t.get("task_id")
                    ]
                else:
                    tid = tool_args.pop("task_id", "")
                    fields = tool_args.pop("fields", None) or tool_args
                    res = jira_service_instance.update_task(task_id=tid, fields=fields)
            else:
                res = update_task_tool.invoke(tool_args)

        elif tool_name == "search_workflow_templates":
            query = tool_args.pop("query", None) or (
                step.action if isinstance(step, PlanStep) else step.get("action", "")
            )
            search_fn = retriever_fn or search_workflow_templates
            try:
                res = search_fn(query=query, **tool_args)
            except (ConnectionError, ResponseHandlingException, UnexpectedResponse):
                res = []

        elif tool_name == "send_notification":
            recipient = (
                tool_args.pop("recipient", None)
                or tool_args.pop("channel", None)
                or tool_args.pop("to", "")
            )
            message = tool_args.pop("message", None) or (
                step.action if isinstance(step, PlanStep) else step.get("action", "")
            )
            if notification_service_instance:
                res = notification_service_instance.send_notification(
                    recipient=recipient, message=message, **tool_args
                )
            else:
                res = send_notification_tool.invoke(
                    {"recipient": recipient, "message": message, **tool_args}
                )

        elif tool_name == "check_calendar_availability":
            user_id = tool_args.pop("user_id", "")
            if not user_id and not tool_args.get("date"):
                logger.info("No-op stub for tool: %s", tool_name)
                res = {"status": "skipped", "tool_name": tool_name}
            else:
                date = tool_args.pop("date", "2026-10-27")
                if calendar_service_instance:
                    res = calendar_service_instance.check_calendar_availability(
                        user_id=user_id, date=date, **tool_args
                    )
                else:
                    res = check_calendar_availability_tool.invoke(
                        {"user_id": user_id, "date": date, **tool_args}
                    )

        else:
            logger.info("No-op stub for tool: %s", tool_name)
            res = {"status": "skipped", "tool_name": tool_name}

    except Exception as err:
        res = {"status": "failed", "error": str(err)}

    results[step_id] = res
    return {
        "current_step_id": step_id,
        "pending_steps": pending,
        "step_results": results,
    }


def verify_step(state: AgentState) -> dict[str, Any]:
    """Verify tool execution outcome and update step tracking lists."""
    step_id = state.get("current_step_id")
    if not step_id:
        return {}

    pending = [s for s in state.get("pending_steps", []) if s != step_id]
    completed = list(state.get("completed_steps", []))
    failed = list(state.get("failed_steps", []))

    result = state.get("step_results", {}).get(step_id)
    is_failed = False
    if result is None:
        is_failed = True
    elif isinstance(result, Exception):
        is_failed = True
    elif isinstance(result, dict) and (
        "error" in result or result.get("status") == "failed"
    ):
        is_failed = True

    if is_failed:
        if step_id not in failed:
            failed.append(step_id)
        status = "failed"
    else:
        if step_id not in completed:
            completed.append(step_id)
        status = "completed"

    for step in state.get("plan", []):
        sid = step.step_id if isinstance(step, PlanStep) else step.get("step_id")
        if sid == step_id:
            if isinstance(step, PlanStep):
                step.status = status
            elif isinstance(step, dict):
                step["status"] = status

    return {
        "pending_steps": pending,
        "completed_steps": completed,
        "failed_steps": failed,
    }


def create_workflow_graph(
    llm=None,
    retriever_fn=None,
    jira_service_instance=None,
    notification_service_instance=None,
    calendar_service_instance=None,
):
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
    workflow.add_node(
        "execute_next_tool",
        lambda state: execute_next_tool(
            state,
            jira_service_instance=jira_service_instance,
            notification_service_instance=notification_service_instance,
            calendar_service_instance=calendar_service_instance,
            retriever_fn=retriever_fn,
        ),
    )
    workflow.add_node("verify_step", verify_step)

    workflow.add_edge(START, "parse_goal")
    workflow.add_edge("parse_goal", "retrieve_sops")
    workflow.add_edge("retrieve_sops", "generate_plan")
    workflow.add_edge("generate_plan", "execute_next_tool")
    workflow.add_edge("execute_next_tool", "verify_step")
    workflow.add_edge("verify_step", END)
    return workflow.compile()


workflow_graph = create_workflow_graph()
