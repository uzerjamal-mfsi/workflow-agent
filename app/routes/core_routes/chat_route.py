from typing import Any

from fastapi import APIRouter

from app.agents.workflow_agent import workflow_graph
from app.exceptions import ValidationError
from app.schemas.core_schemas.chat_schema import ChatRequest, ChatResponse

router = APIRouter()


def format_plan_answer(goal: str, steps: list[Any]) -> str:
    """Format plan steps into a simple response string."""
    return f"Plan for '{goal}' created with {len(steps)} steps."


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Execute the workflow graph via the chat API."""
    query = request.query or request.user_request
    if not query:
        raise ValidationError("Provide a query or user_request.")

    thread_id = request.thread_id or "default"
    config = {"configurable": {"thread_id": thread_id}}
    result = workflow_graph.invoke(
        {"user_request": query, "thread_id": thread_id},
        config=config,
    )
    steps = result.get("plan", [])
    goal = result.get("parsed_goal", query)
    return ChatResponse(
        thread_id=thread_id,
        answer=format_plan_answer(goal, steps),
        plan=steps,
    )
