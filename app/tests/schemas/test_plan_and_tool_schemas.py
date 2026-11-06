from typing import Any, cast

import pytest
from pydantic import ValidationError

from app.schemas.core_schemas.tool_schemas import (
    CheckCalendarArgs,
    CreateTaskArgs,
    SearchTemplatesArgs,
    SendNotificationArgs,
    UpdateTaskArgs,
)
from app.schemas.state import ApprovalDecision, Plan, Step, WorkflowState


def test_create_task_args_defaults():
    args = CreateTaskArgs(title="Write Docs", assignee="dev02")
    assert args.title == "Write Docs"
    assert args.assignee == "dev02"
    assert args.priority == "Medium"


def test_create_task_args_invalid_priority():
    with pytest.raises(ValidationError):
        CreateTaskArgs(title="Task", assignee="dev01", priority="Invalid")  # pyright: ignore[reportArgumentType]


def test_tool_args_instantiation():
    notify_args = SendNotificationArgs(recipient="pm01", message="Deploy ready")
    assert notify_args.recipient == "pm01"
    assert notify_args.message == "Deploy ready"

    cal_args = CheckCalendarArgs(user_id="dev01", date="2026-11-06")
    assert cal_args.user_id == "dev01"
    assert cal_args.date == "2026-11-06"

    update_args = UpdateTaskArgs(task_id="TASK-101", fields={"status": "In Progress"})
    assert update_args.task_id == "TASK-101"
    assert update_args.fields == {"status": "In Progress"}

    search_args = SearchTemplatesArgs(query="deployment workflow")
    assert search_args.query == "deployment workflow"


def test_step_defaults_and_validation():
    step = Step(
        step_id="step_1",
        title="Check dev calendar",
        tool="check_calendar_availability",
        args=CheckCalendarArgs(user_id="dev01", date="2026-11-06"),
    )
    assert step.step_id == "step_1"
    assert step.dependencies == []
    assert step.requires_approval is False
    assert step.expected_outcome == ""


def test_step_invalid_tool():
    with pytest.raises(ValidationError):
        Step(
            step_id="step_1",
            title="Invalid",
            tool=cast(Any, "unsupported_tool"),
            args=SearchTemplatesArgs(query="test"),
        )


def test_plan_instantiation():
    step = Step(
        step_id="step_1",
        title="Send alert",
        tool="send_notification",
        args=SendNotificationArgs(recipient="ops", message="Build failed"),
        requires_approval=True,
    )
    plan = Plan(reasoning="Alert operations on failure", steps=[step])
    assert plan.reasoning == "Alert operations on failure"
    assert len(plan.steps) == 1
    assert plan.steps[0].requires_approval is True


def test_approval_decision_schema_defaults():
    decision = ApprovalDecision(approved=True)
    assert decision.approved is True
    assert decision.feedback is None


def test_approval_decision_schema_with_feedback():
    decision = ApprovalDecision(approved=False, feedback="Action rejected by admin")
    assert decision.approved is False
    assert decision.feedback == "Action rejected by admin"


def test_approval_decision_schema_missing_approved():
    with pytest.raises(ValidationError):
        ApprovalDecision.model_validate({})


def test_workflow_state_last_step_result_field():
    state: WorkflowState = {
        "last_step_result": {
            "step_id": "step_1",
            "tool": "create_task",
            "success": True,
            "output": {"task_id": "TASK-101"},
            "error": None,
        }
    }
    last_step_result = state["last_step_result"]
    assert last_step_result is not None
    assert last_step_result["success"] is True
    assert last_step_result["tool"] == "create_task"

