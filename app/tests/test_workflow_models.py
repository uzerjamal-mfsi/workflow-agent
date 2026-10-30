import pytest
from pydantic import ValidationError

from app.schemas.workflow import AgentState, ExecutionPlan, PlanStep, WorkflowRequest


def test_plan_step_validation():
    """Verify PlanStep validates correctly and applies defaults."""
    step = PlanStep(
        step_id="step_1",
        action="search documentation",
        tool_name="retriever",
        tool_args={"query": "agent workflow"},
    )
    assert step.step_id == "step_1"
    assert step.action == "search documentation"
    assert step.tool_name == "retriever"
    assert step.tool_args == {"query": "agent workflow"}
    assert step.depends_on == []
    assert step.status == "pending"


def test_plan_step_with_dependencies():
    """Verify PlanStep accepts explicit dependencies."""
    step = PlanStep(
        step_id="step_2",
        action="summarize",
        tool_name="summarizer",
        tool_args={},
        depends_on=["step_1"],
    )
    assert step.depends_on == ["step_1"]
    assert step.status == "pending"


def test_execution_plan_validation():
    """Verify ExecutionPlan parses goal and list of steps."""
    plan = ExecutionPlan(
        goal="Answer architecture query",
        steps=[
            PlanStep(
                step_id="step_1",
                action="retrieve info",
                tool_name="retriever",
                tool_args={"query": "test"},
            )
        ],
    )
    assert plan.goal == "Answer architecture query"
    assert len(plan.steps) == 1
    assert plan.steps[0].step_id == "step_1"
    assert plan.steps[0].status == "pending"


def test_workflow_request_validation():
    """Verify WorkflowRequest requires user_request string."""
    req = WorkflowRequest(user_request="Build workflow pipeline")
    assert req.user_request == "Build workflow pipeline"

    with pytest.raises(ValidationError):
        WorkflowRequest()


def test_agent_state_dict():
    """Verify AgentState typed dict accepts expected keys and partial updates."""
    state: AgentState = {
        "user_request": "Execute task",
        "parsed_goal": "Goal description",
        "plan": [
            {
                "step_id": "step_1",
                "action": "run",
                "tool_name": "retriever",
                "tool_args": {},
                "depends_on": [],
                "status": "pending",
            }
        ],
        "completed_steps": ["step_0"],
        "pending_steps": ["step_1"],
        "failed_steps": [],
        "current_step_id": "step_1",
        "step_results": {"step_0": {"status": "ok"}},
    }
    assert state["user_request"] == "Execute task"
    assert len(state["plan"]) == 1
    assert state["completed_steps"] == ["step_0"]
    assert state["pending_steps"] == ["step_1"]
    assert state["current_step_id"] == "step_1"
    assert state["step_results"] == {"step_0": {"status": "ok"}}

    partial_state: AgentState = {"user_request": "Partial task"}
    assert "user_request" in partial_state
