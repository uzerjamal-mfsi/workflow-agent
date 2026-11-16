from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage
from langgraph.graph import END

from app.agents.nodes.classify_intent import classify_intent
from app.agents.workflow_agent import route_after_intent
from app.schemas.state import IntentClassification, WorkflowState


def test_classify_intent_empty_goal():
    state: WorkflowState = {"parsed_goal": ""}
    result = classify_intent(state)
    assert result["is_supported"] is False
    assert "No goal provided" in result["rejection_reason"]
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], AIMessage)


def test_classify_intent_supported_goal():
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = IntentClassification(
        is_supported=True,
        rejection_reason=None,
    )
    mock_llm.with_structured_output.return_value = mock_structured

    with patch(
        "app.agents.nodes.classify_intent.get_llm",
        return_value=mock_llm,
    ):
        state: WorkflowState = {
            "parsed_goal": "Create a high priority task for server outage and notify Alice"
        }
        result = classify_intent(state)
        assert result["is_supported"] is True
        assert result["rejection_reason"] is None


def test_classify_intent_unsupported_goal():
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    rejection = (
        "This type of message is not supported. I only handle operational workflows."
    )
    mock_structured.invoke.return_value = IntentClassification(
        is_supported=False,
        rejection_reason=rejection,
    )
    mock_llm.with_structured_output.return_value = mock_structured

    with patch(
        "app.agents.nodes.classify_intent.get_llm",
        return_value=mock_llm,
    ):
        state: WorkflowState = {"parsed_goal": "Hello! Can you bake me a cake?"}
        result = classify_intent(state)
        assert result["is_supported"] is False
        assert result["rejection_reason"] == rejection
        assert len(result["messages"]) == 1
        assert result["messages"][0].content == rejection


def test_route_after_intent():
    assert route_after_intent({"is_supported": True}) == "retrieve_sops"
    assert route_after_intent({"is_supported": False}) == END
    assert route_after_intent({}) == END
