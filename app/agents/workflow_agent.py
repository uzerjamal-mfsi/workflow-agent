import copy
import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from app.exceptions.domain import TransientError
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

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_TEAM = DATA_DIR / "team_directory.json"

TOOL_PERMISSIONS = {
    "create_task": "task:create",
    "update_task": "task:update",
    "check_calendar_availability": "calendar:read",
}

TARGET_TOOLS = (
    "check_calendar_availability",
    "create_task",
    "update_task",
    "send_notification",
    "search_workflow_templates",
)

WRITE_TOOLS = {
    "create_task",
    "update_task",
    "send_notification",
}

TRANSIENT_EXCEPTIONS = (
    TransientError,
    TimeoutError,
    ConnectionError,
    ResponseHandlingException,
)


def generate_idempotency_key(
    step_id: str, tool_name: str, args: dict[str, Any] | None = None
) -> str:
    """Generate a deterministic hash key for step tool execution."""
    sorted_args = json.dumps(args or {}, sort_keys=True, default=str)
    return hashlib.sha256(f"{step_id}:{tool_name}:{sorted_args}".encode()).hexdigest()


def is_transient_error(error: Any) -> bool:
    """Check if an error represents a retryable transient failure."""
    if isinstance(error, TRANSIENT_EXCEPTIONS):
        return True
    if isinstance(error, Exception):
        msg = str(error).lower()
        return "transient" in msg or "timeout" in msg
    if isinstance(error, dict):
        if error.get("transient") or error.get("is_transient"):
            return True
        err = str(error.get("error", "")).lower()
        return "transient" in err or "timeout" in err
    return False


def _read_team_directory(team_path: str | Path) -> dict[str, Any]:
    path = Path(team_path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _check_step_permission(
    step: PlanStep | dict[str, Any],
    team_data: dict[str, Any],
) -> tuple[bool, str | None]:
    tool = getattr(step, "tool_name", None) or (
        step.get("tool_name", "") if isinstance(step, dict) else ""
    )
    args = getattr(step, "tool_args", None) or (
        step.get("tool_args", {}) if isinstance(step, dict) else {}
    )
    if not isinstance(args, dict):
        args = {}

    user_id = args.get("user_id") or args.get("assignee")
    req_perm = args.get("required_permission") or TOOL_PERMISSIONS.get(tool)

    users = team_data.get("users", [])
    if not users or not user_id:
        return True, None

    user = next((u for u in users if u.get("user_id") == user_id), None)
    if not user:
        return False, f"User '{user_id}' not found in team directory"
    if not user.get("active", True):
        return False, f"User '{user_id}' is inactive"
    if req_perm and req_perm not in user.get("permissions", []):
        return False, f"User '{user_id}' lacks permission '{req_perm}'"

    return True, None


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
        "executed_keys": {},
    }


def validate_dependencies(
    state: AgentState, team_path: str | Path | None = None
) -> dict[str, Any]:
    """Select next runnable step with resolved dependencies and permissions."""
    plan = list(state.get("plan", []))
    pending = list(state.get("pending_steps", []))
    completed = set(state.get("completed_steps", []))
    failed = list(state.get("failed_steps", []))
    results = dict(state.get("step_results", {}))

    plan_map = {
        getattr(s, "step_id", None)
        or (s.get("step_id") if isinstance(s, dict) else ""): s
        for s in plan
    }
    team_data = _read_team_directory(team_path or DEFAULT_TEAM)

    def fail_step(sid: str, error: str):
        if sid in pending:
            pending.remove(sid)
        if sid not in failed:
            failed.append(sid)
        step = plan_map.get(sid)
        if hasattr(step, "status"):
            step.status = "failed"
        elif isinstance(step, dict):
            step["status"] = "failed"
        results[sid] = {"status": "failed", "error": error}

    def cascade_failures():
        changed = True
        while changed:
            changed = False
            for sid in list(pending):
                step = plan_map.get(sid)
                deps = (
                    getattr(step, "depends_on", None)
                    or (step.get("depends_on") if isinstance(step, dict) else [])
                    or []
                )
                if any(d in failed for d in deps):
                    fail_step(sid, "Dependency failed")
                    changed = True

    cascade_failures()

    selected_id = None
    for sid in list(pending):
        step = plan_map.get(sid)
        deps = (
            getattr(step, "depends_on", None)
            or (step.get("depends_on") if isinstance(step, dict) else [])
            or []
        )
        if all(d in completed for d in deps):
            ok, err = _check_step_permission(step, team_data)
            if ok:
                selected_id = sid
            else:
                fail_step(sid, err or "Permission denied")
                cascade_failures()
                selected_id = sid
            break

    if not selected_id and pending:
        for sid in list(pending):
            fail_step(sid, "Unresolvable dependency")
        selected_id = failed[-1] if failed else None

    return {
        "current_step_id": selected_id,
        "pending_steps": pending,
        "failed_steps": failed,
        "step_results": results,
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

    step_id = state.get("current_step_id")
    if not step_id:
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

    results = dict(state.get("step_results", {}))
    executed_keys = dict(state.get("executed_keys") or {})

    # Skip tool execution if already marked failed during validation
    if step_id in failed:
        return {
            "current_step_id": step_id,
            "pending_steps": pending,
            "step_results": results,
            "executed_keys": executed_keys,
        }

    tool_name = (
        step.tool_name if isinstance(step, PlanStep) else step.get("tool_name", "")
    )
    raw_args = (
        step.tool_args if isinstance(step, PlanStep) else step.get("tool_args", {})
    )
    tool_args = copy.deepcopy(raw_args) if isinstance(raw_args, dict) else {}

    # Resolve task_id if it refers to a previously executed step
    raw_task_id = tool_args.get("task_id")
    if raw_task_id and raw_task_id in results:
        prev = results[raw_task_id]
        if isinstance(prev, dict):
            resolved_id = prev.get("task_id") or prev.get("task", {}).get("task_id")
            if resolved_id:
                tool_args["task_id"] = resolved_id

    idempotency_key = None
    if tool_name in WRITE_TOOLS:
        if tool_name == "create_task" and not tool_args.get("title"):
            action = (
                step.action
                if isinstance(step, PlanStep)
                else step.get("action", "")
            )
            tool_args["title"] = action or "Untitled Task"

        idempotency_key = generate_idempotency_key(step_id, tool_name, tool_args)
        if idempotency_key in executed_keys:
            results[step_id] = executed_keys[idempotency_key]
            return {
                "current_step_id": step_id,
                "pending_steps": pending,
                "step_results": results,
                "executed_keys": executed_keys,
            }

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
        res = {
            "status": "failed",
            "error": str(err),
            "transient": is_transient_error(err),
        }

    results[step_id] = res
    if idempotency_key and not (
        isinstance(res, dict) and (res.get("status") == "failed" or "error" in res)
    ):
        executed_keys[idempotency_key] = res

    return {
        "current_step_id": step_id,
        "pending_steps": pending,
        "step_results": results,
        "executed_keys": executed_keys,
    }


def verify_step(state: AgentState) -> dict[str, Any]:
    """Verify tool execution outcome and update step tracking lists."""
    step_id = state.get("current_step_id")
    if not step_id:
        return {}

    pending = list(state.get("pending_steps", []))
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

    step = next(
        (
            s
            for s in state.get("plan", [])
            if (s.step_id if isinstance(s, PlanStep) else s.get("step_id")) == step_id
        ),
        None,
    )

    if is_failed:
        retry_count = (
            getattr(step, "retry_count", 0)
            if isinstance(step, PlanStep)
            else (step.get("retry_count", 0) if isinstance(step, dict) else 0)
        )
        if is_transient_error(result) and retry_count < 2:
            new_retry = retry_count + 1
            if isinstance(step, PlanStep):
                step.retry_count = new_retry
            elif isinstance(step, dict):
                step["retry_count"] = new_retry
            if step_id not in pending:
                pending.insert(0, step_id)
            return {
                "current_step_id": step_id,
                "pending_steps": pending,
                "completed_steps": completed,
                "failed_steps": failed,
            }

        if step_id in pending:
            pending.remove(step_id)
        if step_id not in failed:
            failed.append(step_id)
        status = "failed"
    else:
        if step_id in pending:
            pending.remove(step_id)
        if step_id not in completed:
            completed.append(step_id)
        status = "completed"

    if step:
        if isinstance(step, PlanStep):
            step.status = status
        elif isinstance(step, dict):
            step["status"] = status

    return {
        "pending_steps": pending,
        "completed_steps": completed,
        "failed_steps": failed,
    }


def escalate(state: AgentState) -> dict[str, Any]:
    """Handle step failure by logging and recording escalation."""
    failed_step = state.get("current_step_id")
    logger.warning("Step %s failed, escalating workflow", failed_step)
    return {"escalated": True}


replan = escalate


def route_after_verify(state: AgentState) -> str:
    """Route to validate_dependencies, escalate, execute_next_tool, or END."""
    current_step = state.get("current_step_id")
    failed = state.get("failed_steps", [])
    if (current_step and current_step in failed) or (not current_step and failed):
        return "escalate"

    # Retry active step if transient error occurred and retries remain
    if current_step and current_step in state.get("pending_steps", []):
        results = state.get("step_results", {})
        if is_transient_error(results.get(current_step)):
            return "execute_next_tool"

    pending = state.get("pending_steps", [])
    if pending:
        return "validate_dependencies"

    return END


def create_workflow_graph(
    llm=None,
    retriever_fn=None,
    jira_service_instance=None,
    notification_service_instance=None,
    calendar_service_instance=None,
    team_path=None,
):
    team_file = (
        team_path
        or getattr(jira_service_instance, "team_path", None)
        or getattr(notification_service_instance, "team_path", None)
        or DEFAULT_TEAM
    )

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
        "validate_dependencies",
        lambda state: validate_dependencies(state, team_path=team_file),
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
    workflow.add_node("escalate", escalate)

    workflow.add_edge(START, "parse_goal")
    workflow.add_edge("parse_goal", "retrieve_sops")
    workflow.add_edge("retrieve_sops", "generate_plan")
    workflow.add_edge("generate_plan", "validate_dependencies")
    workflow.add_edge("validate_dependencies", "execute_next_tool")
    workflow.add_edge("execute_next_tool", "verify_step")
    workflow.add_conditional_edges(
        "verify_step",
        route_after_verify,
        {
            "execute_next_tool": "execute_next_tool",
            "validate_dependencies": "validate_dependencies",
            "escalate": "escalate",
            END: END,
        },
    )
    workflow.add_edge("escalate", END)
    return workflow.compile()


workflow_graph = create_workflow_graph()
