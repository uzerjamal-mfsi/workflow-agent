from typing import Annotated, Any

from fastapi import APIRouter, Depends, Security
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.types import Command
from pydantic import BaseModel

from app.agents.checkpointer import get_checkpointer
from app.agents.workflow_agent import get_workflow_graph
from app.auth.api_key import verify_api_key
from app.schemas.core_schemas.chat_schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/v1", dependencies=[Security(verify_api_key)])


class ApprovalRequest(BaseModel):
    thread_id: str
    approved: bool
    feedback: str | None = None


@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    checkpointer: Annotated[BaseCheckpointSaver[Any], Depends(get_checkpointer)],
) -> ChatResponse:
    """Run goal through workflow, saving state to checkpointer under thread_id."""
    graph = get_workflow_graph(checkpointer)

    config: RunnableConfig = {"configurable": {"thread_id": request.thread_id}}

    await graph.ainvoke(
        {
            "user_request": request.message,
            "thread_id": request.thread_id,
            "messages": [request.message],
        },
        config=config,
    )

    return ChatResponse(thread_id=request.thread_id, answer="Test")


@router.post("/chat/approve")
async def approve_endpoint(
    request: ApprovalRequest,
    checkpointer: Annotated[BaseCheckpointSaver[Any], Depends(get_checkpointer)],
):
    graph = get_workflow_graph(checkpointer)
    config: RunnableConfig = {"configurable": {"thread_id": request.thread_id}}

    await graph.ainvoke(
        Command(resume={"approved": request.approved, "feedback": request.feedback}),
        config=config,
    )
    return {"status": "resumed", "thread_id": request.thread_id}
