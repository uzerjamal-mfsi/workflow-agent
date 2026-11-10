from uuid import uuid4

from pydantic import BaseModel, Field

from app.schemas.state import Plan


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
