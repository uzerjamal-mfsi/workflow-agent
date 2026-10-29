from unittest.mock import MagicMock, patch

import pytest

from app.schemas.workflow import ExecutionPlan, PlanStep

DUMMY_STEPS = [
    PlanStep(step_id=f"step_{i}", action=f"action {i}", tool_name="create_task")
    for i in range(1, 5)
]


@pytest.mark.parametrize(
    "payload",
    [
        {"query": "Create an API review task, assign it to dev01 and notify pm01"},
        {"user_request": "Update all overdue high-priority tasks after approval"},
    ],
)
def test_chat_executes_workflow(client, payload):
    """Verify chat endpoint runs workflow and returns structured plan."""
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = ExecutionPlan(
        goal="Task goal", steps=DUMMY_STEPS
    )

    with patch(
        "app.agents.workflow_agent.get_default_chat_client", return_value=mock_llm
    ):
        response = client.post("/api/v1/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert len(data["plan"]) == 4
    assert "Plan for" in data["answer"]


def test_chat_missing_query(client):
    """Verify 422 error when query and user_request are missing."""
    response = client.post("/api/v1/chat", json={})
    assert response.status_code == 422
