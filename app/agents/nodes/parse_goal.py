import re
from typing import Any

from langchain_core.messages import HumanMessage

from app.schemas.state import WorkflowState


def parse_goal(state: WorkflowState) -> dict[str, Any]:
    """Normalizes user request and extract goal"""
    goal = state.get("user_request", "")

    # If goal is empty, gets latest non empty message
    if not goal:
        messages = state.get("messages", [])
        for message in reversed(messages):
            content = (
                message.content
                if hasattr(message, "content")
                else message.get("content", "")
            )
            if content:
                goal = str(content)
                break

    # Clean whitespace and non-printable characters
    cleaned = re.sub(r"[\r\t\f\v]+", " ", goal)
    cleaned = re.sub(r" +", " ", cleaned).strip()

    result: dict[str, Any] = {"parsed_goal": cleaned, "messages": []}
    messages = state.get("messages", [])

    # If the cleaned goal is not the last message, add it
    if cleaned and (not messages or getattr(messages[-1], "content", None) != cleaned):
        result["messages"] = [HumanMessage(content=cleaned)]
    
    return result