from app.schemas.state import Plan, StepResult, WorkflowState

MAX_RETRIES = 3

def verify(state: WorkflowState):
    """Inspects the outcome of execute_next_tool and updates execution state."""
    plan: Plan | None = state.get("plan")
    current_index = state.get("current_step_index", 0)
    last_result: StepResult | None = state.get("last_step_result")
    completed_steps = list(state.get("completed_steps", []))
    failed_steps = list(state.get("failed_steps", []))
    retry_count = state.get("retry_count", 0)

    if not last_result:
        return {"verification_outcome": "escalate"}

    # Success Case
    if last_result.success:
        completed_steps.append(last_result)
        next_index = current_index + 1
        pending_steps = list(plan.steps[next_index:]) if plan else []
        outcome = "completed" if (plan and next_index >= len(plan.steps)) else "next_step"
        return {
            "completed_steps": completed_steps,
            "pending_steps": pending_steps,
            "current_step_index": next_index,
            "retry_count": 0,
            "verification_outcome": outcome,
        }
    
    # Failure: Retry if transient error (step is retrying, not yet failed)
    if last_result.error_type == "transient" and retry_count < MAX_RETRIES:
        return {"retry_count": retry_count + 1, "verification_outcome": "retry"}

    # Step failure (logical error, exhausted transient retries, fatal, or unknown)
    failed_steps.append(last_result)
    pending_steps = list(plan.steps[current_index + 1:]) if plan else []

    if last_result.error_type == "logical":
        return {
            "failed_steps": failed_steps,
            "pending_steps": pending_steps,
            "verification_outcome": "replan",
        }

    return {
        "failed_steps": failed_steps,
        "pending_steps": pending_steps,
        "verification_outcome": "escalate",
    }