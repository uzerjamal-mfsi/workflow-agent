from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Security, status
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.types import Command
from pydantic import BaseModel

from app.agents.checkpointer import get_checkpointer
from app.agents.workflow_agent import get_workflow_graph
from app.auth.api_key import verify_api_key
from app.schemas.core_schemas.chat_schemas import (
    ChatMessageItem,
    ChatRequest,
    ChatResponse,
    WorkflowStatusResponse,
)
from app.schemas.state import Plan

router = APIRouter(prefix="/api/v1", dependencies=[Security(verify_api_key)])


class ApprovalRequest(BaseModel):
    thread_id: str
    approved: bool
    feedback: str | None = None


def extract_chat_history(
    raw_messages: list[Any], latest_answer: str | None = None
) -> list[ChatMessageItem]:
    """Normalize raw LangGraph state messages into clean user/assistant chat history."""
    history: list[ChatMessageItem] = []
    for m in raw_messages:
        content = (
            m.content
            if hasattr(m, "content")
            else (m.get("content") if isinstance(m, dict) else str(m))
        )
        msg_type = (
            getattr(m, "type", None)
            or (m.get("type") if isinstance(m, dict) else None)
        )
        if msg_type in ("ai", "assistant"):
            role = "assistant"
        else:
            role = "user"
        if content:
            history.append(ChatMessageItem(role=role, content=str(content)))

    if latest_answer and (not history or history[-1].role != "assistant"):
        history.append(ChatMessageItem(role="assistant", content=latest_answer))

    return history


@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    checkpointer: Annotated[BaseCheckpointSaver[Any], Depends(get_checkpointer)],
) -> ChatResponse:
    """Run goal through workflow, saving state to checkpointer under thread_id."""
    graph = get_workflow_graph(checkpointer)

    config: RunnableConfig = {"configurable": {"thread_id": request.thread_id}}

    final_state = await graph.ainvoke(
        {
            "user_request": request.message,
            "thread_id": request.thread_id,
            "messages": [request.message],
        },
        config=config,
    )

    plan: Plan | None = final_state.get("plan")

    if final_state.get("requires_approval") and final_state.get("approved") is None:
        status_val = "awaiting_approval"
        answer = "Workflow paused at approval gate for human review."
    elif final_state.get("verification_outcome") == "completed":
        status_val = "completed"
        answer = plan.reasoning if plan and plan.reasoning else "Workflow completed successfully."
    elif final_state.get("verification_outcome") == "escalate":
        status_val = "escalated"
        answer = "Workflow execution escalated due to unrecoverable failure."
    elif final_state.get("approved") is False:
        status_val = "rejected"
        answer = "Workflow was rejected by human reviewer."
    else:
        status_val = "completed"
        answer = plan.reasoning if plan and plan.reasoning else "Workflow processed."

    raw_messages = final_state.get("messages", [])
    chat_history = extract_chat_history(raw_messages, latest_answer=answer)

    return ChatResponse(
        thread_id=request.thread_id,
        answer=answer,
        plan=plan,
        status=status_val,
        messages=chat_history,
    )


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


@router.get("/chat/{thread_id}", response_model=WorkflowStatusResponse)
async def get_chat_state_endpoint(
    thread_id: str,
    checkpointer: Annotated[BaseCheckpointSaver[Any], Depends(get_checkpointer)],
) -> WorkflowStatusResponse:
    """Retrieve current execution state, plan, tool results, and message history for a thread."""
    graph = get_workflow_graph(checkpointer)
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}

    state_snapshot = await graph.aget_state(config)
    if not state_snapshot or not state_snapshot.values:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thread '{thread_id}' not found.",
        )

    values = state_snapshot.values
    plan: Plan | None = values.get("plan")
    next_nodes = state_snapshot.next

    if "approval_gate" in next_nodes:
        wf_status = "awaiting_approval"
        answer = "Workflow paused at approval gate for human review."
    elif values.get("verification_outcome") == "completed":
        wf_status = "completed"
        answer = plan.reasoning if plan and plan.reasoning else "Workflow completed successfully."
    elif values.get("verification_outcome") == "escalate":
        wf_status = "escalated"
        answer = "Workflow execution escalated due to unrecoverable failure."
    elif values.get("approved") is False:
        wf_status = "rejected"
        answer = "Workflow was rejected by human reviewer."
    else:
        wf_status = "completed" if not next_nodes else "running"
        answer = plan.reasoning if plan and plan.reasoning else "Workflow processed."

    raw_messages = values.get("messages", [])
    chat_history = extract_chat_history(raw_messages, latest_answer=answer)

    return WorkflowStatusResponse(
        thread_id=thread_id,
        status=wf_status,
        answer=answer,
        plan=plan,
        current_step_index=values.get("current_step_index", 0),
        completed_steps=values.get("completed_steps", []),
        pending_steps=values.get("pending_steps", []),
        failed_steps=values.get("failed_steps", []),
        requires_approval="approval_gate" in next_nodes,
        next_node=next_nodes[0] if next_nodes else None,
        messages=chat_history,
    )
