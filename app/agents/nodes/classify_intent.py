from typing import Any, cast

from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable

from app.llms.llm_client import get_llm
from app.prompts.classifier_prompt import (
    DEFAULT_UNSUPPORTED_MESSAGE,
    classifier_prompt,
)
from app.schemas.state import IntentClassification, WorkflowState


def classify_intent(state: WorkflowState) -> dict[str, Any]:
    """LangGraph node to classify user intent and determine if request is supported."""
    goal = state.get("parsed_goal", "")
    if not goal:
        return {
            "is_supported": False,
            "rejection_reason": "No goal provided.",
            "messages": [AIMessage(content="No goal provided.")],
        }

    llm = get_llm()
    structured_llm = cast(
        Runnable[Any, IntentClassification],
        llm.with_structured_output(IntentClassification),
    )
    prompt_messages = classifier_prompt.format_messages(goal=goal)
    result = structured_llm.invoke(prompt_messages)

    if not result.is_supported:
        reason = result.rejection_reason or DEFAULT_UNSUPPORTED_MESSAGE
        return {
            "is_supported": False,
            "rejection_reason": reason,
            "messages": [AIMessage(content=reason)],
        }

    return {"is_supported": True, "rejection_reason": None}
