from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage

from app.agents.nodes.parse_goal import parse_goal
from app.prompts.classifier_prompt import DEFAULT_UNSUPPORTED_MESSAGE
from app.schemas.state import IntentClassification, WorkflowState


def test_parse_goal_from_user_request():
    state: WorkflowState = {
        "user_request": "  Process   invoice  \t \n ",
        "messages": [],
    }
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = IntentClassification(is_supported=True)
    mock_llm.with_structured_output.return_value = mock_structured

    with patch("app.agents.nodes.parse_goal.get_llm", return_value=mock_llm):
        result = parse_goal(state)
        assert result["parsed_goal"] == "Process invoice"
        assert result["is_supported"] is True
        assert result["rejection_reason"] is None
        assert len(result["messages"]) == 1
        assert result["messages"][0].content == "Process invoice"
        assert isinstance(result["messages"][0], HumanMessage)


def test_parse_goal_fallback_to_messages():
    state: WorkflowState = {
        "user_request": "",
        "messages": [HumanMessage(content="Deploy the application")],
    }
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = IntentClassification(is_supported=True)
    mock_llm.with_structured_output.return_value = mock_structured

    with patch("app.agents.nodes.parse_goal.get_llm", return_value=mock_llm):
        result = parse_goal(state)
        assert result["parsed_goal"] == "Deploy the application"
        assert result["is_supported"] is True
        assert result["rejection_reason"] is None
        # Should not duplicate message if it matches the last message
        assert result["messages"] == []


def test_parse_goal_empty_goal():
    state: WorkflowState = {
        "user_request": "   \n\t  ",
        "messages": [],
    }
    with patch("app.agents.nodes.parse_goal.get_llm") as mock_get_llm:
        result = parse_goal(state)
        assert result["parsed_goal"] == ""
        assert result["is_supported"] is False
        assert "No goal provided" in result["rejection_reason"]
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)
        assert result["messages"][0].content == result["rejection_reason"]
        mock_get_llm.assert_not_called()


def test_parse_goal_unsupported_goal():
    state: WorkflowState = {
        "user_request": "Can you bake me a chocolate cake?",
        "messages": [],
    }
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    custom_rejection = (
        "Baking requests are not supported. Only platform workflows are supported."
    )
    mock_structured.invoke.return_value = IntentClassification(
        is_supported=False,
        rejection_reason=custom_rejection,
    )
    mock_llm.with_structured_output.return_value = mock_structured

    with patch("app.agents.nodes.parse_goal.get_llm", return_value=mock_llm):
        result = parse_goal(state)
        assert result["parsed_goal"] == "Can you bake me a chocolate cake?"
        assert result["is_supported"] is False
        assert result["rejection_reason"] == custom_rejection
        assert len(result["messages"]) == 2
        assert isinstance(result["messages"][0], HumanMessage)
        assert result["messages"][0].content == "Can you bake me a chocolate cake?"
        assert isinstance(result["messages"][1], AIMessage)
        assert result["messages"][1].content == custom_rejection


def test_parse_goal_unsupported_goal_default_message():
    state: WorkflowState = {
        "user_request": "Tell me a joke",
        "messages": [HumanMessage(content="Tell me a joke")],
    }
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = IntentClassification(
        is_supported=False,
        rejection_reason=None,
    )
    mock_llm.with_structured_output.return_value = mock_structured

    with patch("app.agents.nodes.parse_goal.get_llm", return_value=mock_llm):
        result = parse_goal(state)
        assert result["parsed_goal"] == "Tell me a joke"
        assert result["is_supported"] is False
        assert result["rejection_reason"] == DEFAULT_UNSUPPORTED_MESSAGE
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)
        assert result["messages"][0].content == DEFAULT_UNSUPPORTED_MESSAGE
