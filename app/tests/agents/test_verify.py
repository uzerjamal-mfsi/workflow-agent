from app.agents.nodes.verify import MAX_RETRIES, verify
from app.schemas.core_schemas.tool_schemas import CreateTaskArgs
from app.schemas.state import Plan, Step, StepResult, WorkflowState


def _create_sample_plan(num_steps: int = 2) -> Plan:
    steps = [
        Step(
            step_id=f"step_{i + 1}",
            title=f"Step {i + 1}",
            tool="create_task",
            args=CreateTaskArgs(title=f"Task {i + 1}", assignee="dev01"),
        )
        for i in range(num_steps)
    ]
    return Plan(reasoning="Sample plan", steps=steps)


def test_verify_no_last_step_result():
    state: WorkflowState = {}
    result = verify(state)
    assert result == {"verification_outcome": "escalate"}

    state_none: WorkflowState = {"last_step_result": None}
    assert verify(state_none) == {"verification_outcome": "escalate"}


def test_verify_success_next_step():
    plan = _create_sample_plan(num_steps=2)
    step_result = StepResult(
        step_id="step_1",
        tool="create_task",
        success=True,
        output={"task_id": "TASK-1"},
    )
    state: WorkflowState = {
        "plan": plan,
        "current_step_index": 0,
        "retry_count": 2,
        "last_step_result": step_result,
        "completed_steps": [],
    }

    result = verify(state)
    assert result == {
        "completed_steps": [step_result],
        "current_step_index": 1,
        "retry_count": 0,
        "verification_outcome": "next_step",
    }


def test_verify_success_completed():
    plan = _create_sample_plan(num_steps=1)
    step_result = StepResult(
        step_id="step_1",
        tool="create_task",
        success=True,
        output={"task_id": "TASK-1"},
    )
    state: WorkflowState = {
        "plan": plan,
        "current_step_index": 0,
        "last_step_result": step_result,
    }

    result = verify(state)
    assert result == {
        "completed_steps": [step_result],
        "current_step_index": 1,
        "retry_count": 0,
        "verification_outcome": "completed",
    }


def test_verify_success_without_plan():
    step_result = StepResult(
        step_id="step_1",
        tool="create_task",
        success=True,
        output={"status": "ok"},
    )
    state: WorkflowState = {
        "plan": None,
        "current_step_index": 0,
        "last_step_result": step_result,
    }

    result = verify(state)
    assert result == {
        "completed_steps": [step_result],
        "current_step_index": 1,
        "retry_count": 0,
        "verification_outcome": "next_step",
    }


def test_verify_success_preserves_existing_completed_steps():
    prior_result = StepResult(
        step_id="step_1",
        tool="create_task",
        success=True,
        output={"task_id": "TASK-1"},
    )
    new_result = StepResult(
        step_id="step_2",
        tool="create_task",
        success=True,
        output={"task_id": "TASK-2"},
    )
    plan = _create_sample_plan(num_steps=2)
    state: WorkflowState = {
        "plan": plan,
        "current_step_index": 1,
        "completed_steps": [prior_result],
        "last_step_result": new_result,
    }

    result = verify(state)
    assert result["completed_steps"] == [prior_result, new_result]
    assert result["verification_outcome"] == "completed"


def test_verify_logical_error():
    step_result = StepResult(
        step_id="step_1",
        tool="create_task",
        success=False,
        error="Invalid parameter value",
        error_type="logical",
    )
    state: WorkflowState = {
        "last_step_result": step_result,
    }

    result = verify(state)
    assert result == {"verification_outcome": "replan"}


def test_verify_transient_error_retry():
    step_result = StepResult(
        step_id="step_1",
        tool="create_task",
        success=False,
        error="Connection reset",
        error_type="transient",
    )
    state: WorkflowState = {
        "last_step_result": step_result,
        "retry_count": 0,
    }

    result = verify(state)
    assert result == {
        "retry_count": 1,
        "verification_outcome": "retry",
    }


def test_verify_transient_error_escalate_when_max_retries_reached():
    step_result = StepResult(
        step_id="step_1",
        tool="create_task",
        success=False,
        error="Connection reset",
        error_type="transient",
    )
    state: WorkflowState = {
        "last_step_result": step_result,
        "retry_count": MAX_RETRIES,
    }

    result = verify(state)
    assert result == {"verification_outcome": "escalate"}


def test_verify_fatal_error():
    step_result = StepResult(
        step_id="step_1",
        tool="create_task",
        success=False,
        error="Database crashed",
        error_type="fatal",
    )
    state: WorkflowState = {
        "last_step_result": step_result,
    }

    result = verify(state)
    assert result == {"verification_outcome": "escalate"}


def test_verify_unknown_error_type():
    step_result = StepResult(
        step_id="step_1",
        tool="create_task",
        success=False,
        error="Unexpected failure",
        error_type=None,
    )
    state: WorkflowState = {
        "last_step_result": step_result,
    }

    result = verify(state)
    assert result == {"verification_outcome": "escalate"}

