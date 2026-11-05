from uuid import uuid4

from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Raw Message/Input")
    thread_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Session Thread ID for conversational memory"
    )

class ChatResponse(BaseModel):
    thread_id: str = Field(..., description="Conversation thread id")
    answer: str = Field(..., description="Final Answer")