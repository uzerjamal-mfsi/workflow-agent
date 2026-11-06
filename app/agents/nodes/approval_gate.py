from typing import Any

from langgraph.types import interrupt

from app.schemas.state import ApprovalDecision, Plan, WorkflowState

def approval_gate(state: WorkflowState):
    """Human-in-the-Loop approval gate node."""
    
    # Reject invalid plan
    if not state.get("is_plan_valid", False):
        return {
            "approved": False,
            "feedback": "Plan validation failed.",
        }
    
    plan: Plan | None = state.get("plan")
    if not plan or not plan.steps:
        return {
            "approved": False,
            "feedback": "No plan found.",
        }
    
    # No Approval Required
    if not state.get("requires_approval", False):
        return {
            "approved": True,
            "feedback": None,
        }
    
    raw_response = interrupt({
        "thread_id": state.get("thread_id", ""),
        "plan": plan.model_dump(),
        "prompt": "Review sensitive actions. Approve or provide feedback.",
    })

    decision = ApprovalDecision.model_validate(raw_response)   

    return {
        "approved": decision.approved,
        "feedback": decision.feedback,
    }