from typing import Any, TypedDict

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    step_id: str
    action: str
    tool_name: str
    tool_args: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)


class ExecutionPlan(BaseModel):
    goal: str
    steps: list[PlanStep] = Field(default_factory=list)


class WorkflowRequest(BaseModel):
    user_request: str


class AgentState(TypedDict, total=False):
    user_request: str
    parsed_goal: str
    plan: list[PlanStep] | list[dict[str, Any]]
