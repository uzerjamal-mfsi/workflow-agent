from typing import Annotated, Any

from fastapi import APIRouter, Depends
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.agents.checkpointer import get_checkpointer
from app.agents.workflow_agent import create_workflow_graph
from app.schemas.core_schemas.chat_schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/v1")

@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest, 
    checkpointer: Annotated[BaseCheckpointSaver[Any], Depends(get_checkpointer)]
) -> ChatResponse:
    """Run goal through workflow, saving state to checkpointer under thread_id."""
    graph = create_workflow_graph(checkpointer)

    config: RunnableConfig = {
        "configurable": {
            "thread_id": request.thread_id
        }
    }

    await graph.ainvoke(
        {
            "user_request": request.message, 
            "thread_id": request.thread_id, 
            "messages": [request.message]
        },
        config=config
    )

    return ChatResponse(
        thread_id=request.thread_id,
        answer="Test"
    )