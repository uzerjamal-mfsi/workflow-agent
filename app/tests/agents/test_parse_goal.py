from langchain_core.messages import HumanMessage

from app.agents.nodes.parse_goal import parse_goal
from app.schemas.state import WorkflowState


def test_parse_goal_from_user_request():
    state: WorkflowState = {
        "user_request": "  Process   invoice  \t \n ",
        "messages": [],
    }
    result = parse_goal(state)
    assert result["parsed_goal"] == "Process invoice"
    assert len(result["messages"]) == 1
    assert result["messages"][0].content == "Process invoice"


def test_parse_goal_fallback_to_messages():
    state: WorkflowState = {
        "user_request": "",
        "messages": [HumanMessage(content="Deploy the application")],
    }
    result = parse_goal(state)
    assert result["parsed_goal"] == "Deploy the application"
    # Should not duplicate message if it matches the last message
    assert result["messages"] == []
