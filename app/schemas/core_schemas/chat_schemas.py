from uuid import uuid4

from pydantic import BaseModel, Field

from app.schemas.state import Plan, Step, StepResult


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Raw Message/Input")
    thread_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Session Thread ID for conversational memory",
    )


class ChatResponse(BaseModel):
    thread_id: str = Field(..., description="Conversation thread id")
    answer: str = Field(..., description="Final Answer")
    plan: Plan | None = Field(
        default=None, description="Generated structured execution plan"
    )
    status: str = Field(
        default="completed", description="Workflow execution status"
    )


class WorkflowStatusResponse(BaseModel):
    thread_id: str = Field(..., description="Conversation thread id")
    status: str = Field(
        ...,
        description="Workflow execution status: awaiting_approval, completed, rejected, escalated, running",
    )
    answer: str = Field(..., description="Final Answer or status description")
    plan: Plan | None = Field(
        default=None, description="Generated structured execution plan"
    )
    current_step_index: int = Field(default=0, description="Current step index")
    completed_steps: list[StepResult] = Field(
        default_factory=list, description="List of completed steps and outputs"
    )
    pending_steps: list[Step] = Field(
        default_factory=list, description="List of pending steps"
    )
    failed_steps: list[StepResult] = Field(
        default_factory=list, description="List of failed steps"
    )
    requires_approval: bool = Field(
        default=False, description="Whether workflow is waiting for approval"
    )
    next_node: str | None = Field(
        default=None, description="Next node waiting for input if interrupted"
    )
