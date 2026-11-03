from typing import Any

from fastapi import APIRouter

from app.agents.workflow_agent import workflow_graph
from app.exceptions import ValidationError
from app.schemas.core_schemas.chat_schema import ChatRequest, ChatResponse

router = APIRouter()


def format_plan_answer(goal: str, steps: list[Any]) -> str:
    """Format plan steps into a simple response string."""
    return f"Plan for '{goal}' created with {len(steps)} steps."


def serialize_message(msg: Any) -> dict[str, Any]:
    """Convert a message object or dict into a standard dictionary."""
    if isinstance(msg, dict):
        return msg
    role = getattr(msg, "type", "user")
    if role == "human":
        role = "user"
    elif role == "ai":
        role = "assistant"
    return {"role": role, "content": getattr(msg, "content", str(msg))}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Execute the workflow graph via the chat API."""
    query = request.query or request.user_request
    if not query and request.messages:
        query = request.messages[-1].get("content")
    if not query:
        raise ValidationError("Provide a query or user_request.")

    thread_id = request.thread_id or "default"
    config = {"configurable": {"thread_id": thread_id}}
    user_msg = {"role": "user", "content": query}
    result = workflow_graph.invoke(
        {"user_request": query, "thread_id": thread_id, "messages": [user_msg]},
        config=config,
    )
    steps = result.get("plan", [])
    goal = result.get("parsed_goal", query)
    answer = format_plan_answer(goal, steps)

    ai_msg = {"role": "assistant", "content": answer}
    workflow_graph.update_state(config, {"messages": [ai_msg]})

    state = workflow_graph.get_state(config)
    raw_messages = state.values.get("messages", result.get("messages", []))
    history = [serialize_message(m) for m in raw_messages]

    return ChatResponse(
        thread_id=thread_id,
        answer=answer,
        plan=steps,
        history=history,
        messages=history,
    )
