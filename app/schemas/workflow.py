from typing import Any, TypedDict

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    step_id: str
    action: str
    tool_name: str
    tool_args: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    status: str = "pending"


class ExecutionPlan(BaseModel):
    goal: str
    steps: list[PlanStep] = Field(default_factory=list)


class WorkflowRequest(BaseModel):
    user_request: str


class AgentState(TypedDict, total=False):
    user_request: str
    parsed_goal: str
    retrieved_sops: list[dict[str, Any]]
    plan: list[PlanStep] | list[dict[str, Any]]
    completed_steps: list[str]
    pending_steps: list[str]
    failed_steps: list[str]
    current_step_id: str | None
    step_results: dict[str, Any]
    escalated: bool
