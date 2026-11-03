from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    step_id: str
    action: str
    tool_name: str
    tool_args: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    status: str = "pending"
    retry_count: int = 0


class ExecutionPlan(BaseModel):
    goal: str
    steps: list[PlanStep] = Field(default_factory=list)


class WorkflowRequest(BaseModel):
    user_request: str


class AgentState(TypedDict, total=False):
    messages: Annotated[list[Any], add_messages]
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
    executed_keys: dict[str, Any]
    thread_id: str | None
    workflow_status: str
