import re
from typing import Any, cast

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import Runnable

from app.llms.llm_client import get_llm
from app.prompts.classifier_prompt import (
    DEFAULT_UNSUPPORTED_MESSAGE,
    classifier_prompt,
)
from app.schemas.state import IntentClassification, WorkflowState


def parse_goal(state: WorkflowState) -> dict[str, Any]:
    """Normalizes user request, extracts goal, and verifies intent via LLM."""
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

    messages = state.get("messages", [])
    new_messages: list[Any] = []

    # If the cleaned goal is not the last message, add it
    if cleaned and (not messages or getattr(messages[-1], "content", None) != cleaned):
        new_messages.append(HumanMessage(content=cleaned))

    if not cleaned:
        rejection_reason = "No goal provided."
        new_messages.append(AIMessage(content=rejection_reason))
        return {
            "parsed_goal": "",
            "is_supported": False,
            "rejection_reason": rejection_reason,
            "messages": new_messages,
        }

    # Intent guessing via LLM
    llm = get_llm()
    structured_llm = cast(
        Runnable[Any, IntentClassification],
        llm.with_structured_output(IntentClassification),
    )
    prompt_messages = classifier_prompt.format_messages(goal=cleaned)
    classification = structured_llm.invoke(prompt_messages)

    if not classification.is_supported:
        reason = classification.rejection_reason or DEFAULT_UNSUPPORTED_MESSAGE
        new_messages.append(AIMessage(content=reason))
        return {
            "parsed_goal": cleaned,
            "is_supported": False,
            "rejection_reason": reason,
            "messages": new_messages,
        }

    return {
        "parsed_goal": cleaned,
        "is_supported": True,
        "rejection_reason": None,
        "messages": new_messages,
    }
