from typing import Any

from pydantic import BaseModel

from app.schemas.state import Plan, Step, WorkflowState

SENSITIVE_TOOLS = {"send_notification"}

def _get_arg(args: Any, key: str) -> Any:
    """Safely extracts argument values whether args is a Pydantic model or dict."""
    if isinstance(args, BaseModel):
        return getattr(args, key, None)
    if isinstance(args, dict):
        return args.get(key)
    return None

def validate_dag_dependencies(steps: list[Step]) -> list[str]:
    """
    Validates step ordering and acyclic dependencies:
    1. Dependencies must reference real step_ids in the plan.
    2. A step cannot depend on itself.
    3. Dependencies must appear BEFORE the dependent step.
    """

    errors: list[str] = []
    all_step_ids = {s.step_id for s in steps}
    seen_step_ids: set[str] = set()

    for step in steps:
        for dep in step.dependencies:
            if dep not in all_step_ids:
                errors.append(
                    f"Step '{step.step_id}' depends on non-existent step '{dep}'."
                )
            elif dep == step.step_id:
                errors.append(
                    f"Step '{step.step_id}' cannot depend on itself."
                )
            elif dep not in seen_step_ids:
                errors.append(
                    f"Step '{step.step_id}' depends on step '{dep}' which appears later (out-of-order or cycle)."
                )
        seen_step_ids.add(step.step_id)
    
    return errors
    
def enforce_permission_policy(steps: list[Step]) -> bool:
    """
    Enforces autonomous vs. human-in-the-loop policies (SOP Section 6).
    If a tool is classified as sensitive or performs bulk updates,
    forces step.requires_approval = True.
    
    Returns True if any step in the plan requires human approval.
    """
    plan_requires_approval = False

    for step in steps:
        # Mandatory approval for external notifications
        if step.tool in SENSITIVE_TOOLS:
            step.requires_approval = True
        #  Mandatory approval for bulk updates
        if step.tool == "update_task":
            fields = _get_arg(step.args, "fields") or {}
            if "bulk" in str(fields).lower() or isinstance(fields.get("task_ids"), list):
                step.requires_approval = True # Steo level approval
        if step.requires_approval:
            plan_requires_approval = True # Plan level approval

    return plan_requires_approval


def validate_dependencies_and_permission(state: WorkflowState) -> dict[str, Any]:
    """LangGraph node to validate plan DAG dependencies, enforce security policies and initialize execution state."""

    plan: Plan | None = state.get("plan")
    if not plan or not plan.steps:
        return {
            "is_plan_valid": False,
            "validation_errors": ["No plan or steps found to validate."],
            "requires_approval": False,
            "current_step_index": 0,
            "completed_steps": [],
            "failed_steps": [],
        }
    
    # DAG validation
    errors = validate_dag_dependencies(plan.steps)

    # Permission and Policy
    requires_approval = enforce_permission_policy(plan.steps)

    is_valid = len(errors) == 0

    return {
        "is_plan_valid": is_valid,
        "validation_errors": errors,
        "requires_approval": requires_approval,
        "current_step_index": 0,
        "completed_steps": [],
        "failed_steps": [],
    }