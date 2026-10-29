from typing import Any

from pydantic import BaseModel, Field

from app.schemas.workflow import PlanStep


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    thread_id: str = Field(default="default", description="Conversation thread id")
    query: str | None = Field(default=None, description="User query")
    user_request: str | None = Field(default=None, description="Workflow user request")


class ChatResponse(BaseModel):
    """Response body for chat endpoint."""

    thread_id: str = Field(..., description="Conversation thread id")
    answer: str = Field(..., description="Assistant response")
    plan: list[PlanStep] | list[dict[str, Any]] = Field(
        default_factory=list, description="Generated execution plan steps"
    )
