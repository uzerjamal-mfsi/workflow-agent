from unittest.mock import patch

from app.agents.nodes.approval_gate import approval_gate
from app.schemas.core_schemas.tool_schemas import CreateTaskArgs
from app.schemas.state import Plan, Step, WorkflowState


def _create_sample_plan() -> Plan:
    return Plan(
        reasoning="Test plan reasoning",
        steps=[
            Step(
                step_id="step_1",
                title="Create task",
                tool="create_task",
                args=CreateTaskArgs(title="Test Task", assignee="dev01"),
                requires_approval=True,
            )
        ],
    )


def test_approval_gate_plan_invalid():
    state: WorkflowState = {
        "is_plan_valid": False,
        "plan": _create_sample_plan(),
    }
    result = approval_gate(state)
    assert result == {
        "approved": False,
        "feedback": "Plan validation failed.",
    }


def test_approval_gate_missing_plan_validity_flag():
    state: WorkflowState = {
        "plan": _create_sample_plan(),
    }
    result = approval_gate(state)
    assert result == {
        "approved": False,
        "feedback": "Plan validation failed.",
    }


def test_approval_gate_no_plan():
    state: WorkflowState = {
        "is_plan_valid": True,
        "plan": None,
    }
    result = approval_gate(state)
    assert result == {
        "approved": False,
        "feedback": "No plan found.",
    }


def test_approval_gate_empty_plan_steps():
    state: WorkflowState = {
        "is_plan_valid": True,
        "plan": Plan(reasoning="Empty plan", steps=[]),
    }
    result = approval_gate(state)
    assert result == {
        "approved": False,
        "feedback": "No plan found.",
    }


def test_approval_gate_no_approval_required():
    state: WorkflowState = {
        "is_plan_valid": True,
        "plan": _create_sample_plan(),
        "requires_approval": False,
    }
    with patch("app.agents.nodes.approval_gate.interrupt") as mock_interrupt:
        result = approval_gate(state)
        assert result == {
            "approved": True,
            "feedback": None,
        }
        mock_interrupt.assert_not_called()


def test_approval_gate_approval_required_approved():
    plan = _create_sample_plan()
    state: WorkflowState = {
        "thread_id": "thread-abc-123",
        "is_plan_valid": True,
        "plan": plan,
        "requires_approval": True,
    }
    with patch("app.agents.nodes.approval_gate.interrupt") as mock_interrupt:
        mock_interrupt.return_value = {"approved": True, "feedback": None}

        result = approval_gate(state)

        assert result == {
            "approved": True,
            "feedback": None,
        }
        mock_interrupt.assert_called_once_with({
            "thread_id": "thread-abc-123",
            "plan": plan.model_dump(),
            "prompt": "Review sensitive actions. Approve or provide feedback.",
        })


def test_approval_gate_approval_required_rejected_with_feedback():
    plan = _create_sample_plan()
    state: WorkflowState = {
        "thread_id": "thread-xyz-789",
        "is_plan_valid": True,
        "plan": plan,
        "requires_approval": True,
    }
    with patch("app.agents.nodes.approval_gate.interrupt") as mock_interrupt:
        mock_interrupt.return_value = {
            "approved": False,
            "feedback": "Action rejected due to high risk.",
        }

        result = approval_gate(state)

        assert result == {
            "approved": False,
            "feedback": "Action rejected due to high risk.",
        }
        mock_interrupt.assert_called_once_with({
            "thread_id": "thread-xyz-789",
            "plan": plan.model_dump(),
            "prompt": "Review sensitive actions. Approve or provide feedback.",
        })

