from app.agents.nodes.validate_dependencies_and_permissions import (
    enforce_permission_policy,
    validate_dag_dependencies,
    validate_dependencies_and_permission,
)
from app.schemas.core_schemas.tool_schemas import (
    CreateTaskArgs,
    SendNotificationArgs,
    UpdateTaskArgs,
)
from app.schemas.state import Plan, Step, WorkflowState


def test_validate_dag_dependencies_valid():
    steps = [
        Step(
            step_id="step_1",
            title="Create Task",
            tool="create_task",
            args=CreateTaskArgs(title="Task 1", assignee="dev01"),
            dependencies=[],
        ),
        Step(
            step_id="step_2",
            title="Notify Assignee",
            tool="send_notification",
            args=SendNotificationArgs(recipient="pm01", message="Done"),
            dependencies=["step_1"],
        ),
    ]
    errors = validate_dag_dependencies(steps)
    assert errors == []


def test_validate_dag_dependencies_non_existent():
    steps = [
        Step(
            step_id="step_1",
            title="Create Task",
            tool="create_task",
            args=CreateTaskArgs(title="Task 1", assignee="dev01"),
            dependencies=["non_existent_step"],
        )
    ]
    errors = validate_dag_dependencies(steps)
    assert len(errors) == 1
    assert "depends on non-existent step 'non_existent_step'" in errors[0]


def test_validate_dag_dependencies_self_dependency():
    steps = [
        Step(
            step_id="step_1",
            title="Create Task",
            tool="create_task",
            args=CreateTaskArgs(title="Task 1", assignee="dev01"),
            dependencies=["step_1"],
        )
    ]
    errors = validate_dag_dependencies(steps)
    assert len(errors) == 1
    assert "cannot depend on itself" in errors[0]


def test_validate_dag_dependencies_out_of_order_or_cycle():
    steps = [
        Step(
            step_id="step_1",
            title="Step 1",
            tool="create_task",
            args=CreateTaskArgs(title="Task 1", assignee="dev01"),
            dependencies=["step_2"],
        ),
        Step(
            step_id="step_2",
            title="Step 2",
            tool="create_task",
            args=CreateTaskArgs(title="Task 2", assignee="dev02"),
            dependencies=[],
        ),
    ]
    errors = validate_dag_dependencies(steps)
    assert len(errors) == 1
    assert "appears later (out-of-order or cycle)" in errors[0]


def test_enforce_permission_policy_standard_tool():
    steps = [
        Step(
            step_id="step_1",
            title="Create Task",
            tool="create_task",
            args=CreateTaskArgs(title="Task 1", assignee="dev01"),
            requires_approval=False,
        )
    ]
    requires_approval = enforce_permission_policy(steps)
    assert requires_approval is False
    assert steps[0].requires_approval is False


def test_enforce_permission_policy_sensitive_tool():
    steps = [
        Step(
            step_id="step_1",
            title="Send Notification",
            tool="send_notification",
            args=SendNotificationArgs(recipient="dev01", message="Alert"),
            requires_approval=False,
        )
    ]
    requires_approval = enforce_permission_policy(steps)
    assert requires_approval is True
    assert steps[0].requires_approval is True


def test_enforce_permission_policy_bulk_update():
    steps = [
        Step(
            step_id="step_1",
            title="Update Multiple Tasks",
            tool="update_task",
            args=UpdateTaskArgs(
                task_id="TASK-1",
                fields={"task_ids": ["TASK-1", "TASK-2"], "status": "Closed"},
            ),
            requires_approval=False,
        )
    ]
    requires_approval = enforce_permission_policy(steps)
    assert requires_approval is True
    assert steps[0].requires_approval is True


def test_validate_dependencies_and_permission_missing_or_empty_plan():
    state: WorkflowState = {}
    result = validate_dependencies_and_permission(state)

    assert result["is_plan_valid"] is False
    assert result["validation_errors"] == ["No plan or steps found to validate."]
    assert result["requires_approval"] is False
    assert result["current_step_index"] == 0
    assert result["completed_steps"] == []
    assert result["failed_steps"] == []
    assert result["pending_steps"] == []


def test_validate_dependencies_and_permission_valid_plan():
    step1 = Step(
        step_id="step_1",
        title="Create Task",
        tool="create_task",
        args=CreateTaskArgs(title="Task 1", assignee="dev01"),
    )
    state: WorkflowState = {
        "plan": Plan(
            reasoning="Valid plan",
            steps=[step1],
        )
    }
    result = validate_dependencies_and_permission(state)

    assert result["is_plan_valid"] is True
    assert result["validation_errors"] == []
    assert result["requires_approval"] is False
    assert result["current_step_index"] == 0
    assert result["completed_steps"] == []
    assert result["failed_steps"] == []
    assert result["pending_steps"] == [step1]


def test_validate_dependencies_and_permission_invalid_plan():
    state: WorkflowState = {
        "plan": Plan(
            reasoning="Invalid plan with self-dependency",
            steps=[
                Step(
                    step_id="step_1",
                    title="Task Self-Dep",
                    tool="create_task",
                    args=CreateTaskArgs(title="Task 1", assignee="dev01"),
                    dependencies=["step_1"],
                )
            ],
        )
    }
    result = validate_dependencies_and_permission(state)

    assert result["is_plan_valid"] is False
    assert isinstance(result["validation_errors"], list)
    assert len(result["validation_errors"]) == 1
    assert "cannot depend on itself" in result["validation_errors"][0]

