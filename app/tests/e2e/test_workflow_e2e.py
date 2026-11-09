"""End-to-End test suite for the Workflow Agent.

Covers the full user journey through the REST API (/api/v1/chat, /api/v1/chat/approve)
1. Autonomous execution (task creation)
2. Autonomous execution (calendar availability)
3. Sensitive action (approval gate -> human approved -> executed)
4. Sensitive action (approval gate -> human rejected -> stopped)
5. Human feedback replan (rejected with feedback -> re-planned -> executed)
6. Multi-step dependency execution (step 1 -> step 2 -> completed)
7. Transient error retry & recovery (network glitch -> retry -> completed)
8. Transient error escalation (max retries exceeded -> escalate)
9. Logical error recovery (invalid parameter -> replan -> completed)
10. Bulk update security policy (bulk flag -> approval gate -> approved -> completed)
"""

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from langgraph.checkpoint.memory import MemorySaver

import app.agents.workflow_agent as workflow_agent
from app.agents.checkpointer import get_checkpointer
from app.main import app
from app.schemas.core_schemas.tool_schemas import (
    CheckCalendarArgs,
    CreateTaskArgs,
    SendNotificationArgs,
    UpdateTaskArgs,
)
from app.schemas.state import Plan, Step


def make_step(
    step_id: str, tool: str, args: Any, deps: list[str] | None = None
) -> Step:
    """Helper to build a concise workflow step."""
    return Step(
        step_id=step_id, title=tool, tool=tool, args=args, dependencies=deps or []
    )


def make_plan(steps: list[Step]) -> Plan:
    """Helper to wrap steps into a structured plan."""
    return Plan(reasoning="e2e test plan", steps=steps)


@pytest.fixture
def memory_checkpointer() -> MemorySaver:
    return MemorySaver()


@pytest.fixture
async def e2e_env(
    memory_checkpointer: MemorySaver,
) -> AsyncGenerator[tuple[AsyncClient, Any, MagicMock, AsyncMock], None]:
    """Sets up FastAPI test client, in-memory checkpointer, and mocks external boundaries."""
    app.dependency_overrides[get_checkpointer] = lambda: memory_checkpointer
    workflow_agent._compiled_graph = None

    with (
        patch("app.agents.nodes.retrieve_sops.get_embedding_provider"),
        patch("app.agents.nodes.retrieve_sops.get_qdrant_repository"),
        patch(
            "app.agents.nodes.retrieve_sops.search_sops", return_value=["Standard SOP"]
        ),
        patch("app.agents.nodes.generate_structured_plan.get_llm") as mock_get_llm,
        patch(
            "app.agents.nodes.execute_new_tool._run_tool", new_callable=AsyncMock
        ) as mock_run_tool,
    ):
        mock_structured = MagicMock()
        mock_get_llm.return_value.with_structured_output.return_value = mock_structured

        async def get_state(thread_id: str):
            graph = workflow_agent.get_workflow_graph(memory_checkpointer)
            return await graph.aget_state({"configurable": {"thread_id": thread_id}})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, get_state, mock_structured.invoke, mock_run_tool

    app.dependency_overrides.clear()
    workflow_agent._compiled_graph = None


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_autonomous_create_task(e2e_env):
    """1. Autonomous task creation runs to completion without human approval."""
    client, get_state, mock_planner, mock_tool = e2e_env
    mock_planner.return_value = make_plan(
        [
            make_step(
                "s1",
                "create_task",
                CreateTaskArgs(title="Fix bug", assignee="dev01"),
            )
        ]
    )
    mock_tool.return_value = {"task_id": "TASK-101", "status": "Open"}

    res = await client.post(
        "/api/v1/chat", json={"message": "Fix login bug", "thread_id": "t1"}
    )
    assert res.status_code == 200

    state = await get_state("t1")
    assert state.next == ()
    assert state.values["verification_outcome"] == "completed"
    assert state.values["completed_steps"][0].output == {
        "task_id": "TASK-101",
        "status": "Open",
    }


@pytest.mark.asyncio
async def test_e2e_autonomous_check_calendar(e2e_env):
    """2. Read-only calendar check runs autonomously and returns free slots."""
    client, get_state, mock_planner, mock_tool = e2e_env
    mock_planner.return_value = make_plan(
        [
            make_step(
                "s1",
                "check_calendar_availability",
                CheckCalendarArgs(user_id="dev01", date="2026-11-15"),
            )
        ]
    )
    mock_tool.return_value = {"available_slots": ["09:00", "14:00"]}

    res = await client.post(
        "/api/v1/chat", json={"message": "Check schedule", "thread_id": "t2"}
    )
    assert res.status_code == 200

    state = await get_state("t2")
    assert state.next == ()
    assert state.values["verification_outcome"] == "completed"
    assert state.values["completed_steps"][0].output["available_slots"] == [
        "09:00",
        "14:00",
    ]


@pytest.mark.asyncio
async def test_e2e_sensitive_notification_approved(e2e_env):
    """3. Sensitive notification interrupts at approval gate and completes once approved."""
    client, get_state, mock_planner, mock_tool = e2e_env
    mock_planner.return_value = make_plan(
        [
            make_step(
                "s1",
                "send_notification",
                SendNotificationArgs(recipient="all@co.com", message="Alert"),
            )
        ]
    )
    mock_tool.return_value = {"status": "sent"}

    # Request pauses at approval gate
    await client.post(
        "/api/v1/chat", json={"message": "Send alert", "thread_id": "t3"}
    )
    state = await get_state("t3")
    assert state.next == ("approval_gate",)
    mock_tool.assert_not_called()

    # User approves -> resumes and finishes
    res = await client.post(
        "/api/v1/chat/approve", json={"thread_id": "t3", "approved": True}
    )
    assert res.status_code == 200
    state = await get_state("t3")
    assert state.next == ()
    assert state.values["verification_outcome"] == "completed"
    assert state.values["completed_steps"][0].output == {"status": "sent"}


@pytest.mark.asyncio
async def test_e2e_sensitive_notification_rejected(e2e_env):
    """4. Sensitive notification rejected by user halts immediately without tool execution."""
    client, get_state, mock_planner, mock_tool = e2e_env
    mock_planner.return_value = make_plan(
        [
            make_step(
                "s1",
                "send_notification",
                SendNotificationArgs(recipient="all@co.com", message="Alert"),
            )
        ]
    )

    await client.post(
        "/api/v1/chat", json={"message": "Send alert", "thread_id": "t4"}
    )
    assert (await get_state("t4")).next == ("approval_gate",)

    # User rejects without feedback -> workflow ends
    res = await client.post(
        "/api/v1/chat/approve", json={"thread_id": "t4", "approved": False}
    )
    assert res.status_code == 200

    state = await get_state("t4")
    assert state.next == ()
    assert state.values["approved"] is False
    assert len(state.values.get("completed_steps", [])) == 0
    mock_tool.assert_not_called()


@pytest.mark.asyncio
async def test_e2e_human_feedback_triggers_replan(e2e_env):
    """5. Rejection with feedback triggers replanning and executes revised plan."""
    client, get_state, mock_planner, mock_tool = e2e_env
    plan_initial = make_plan(
        [
            make_step(
                "s1",
                "send_notification",
                SendNotificationArgs(recipient="boss@co.com", message="Hi"),
            )
        ]
    )
    plan_revised = make_plan(
        [
            make_step(
                "s2",
                "create_task",
                CreateTaskArgs(title="Prepare report", assignee="dev02"),
            )
        ]
    )
    mock_planner.side_effect = (
        lambda msgs: plan_revised
        if any("[USER REPLAN FEEDBACK]" in m.content for m in msgs)
        else plan_initial
    )
    mock_tool.return_value = {"task_id": "TASK-202", "assignee": "dev02"}

    await client.post(
        "/api/v1/chat", json={"message": "Report status", "thread_id": "t5"}
    )
    assert (await get_state("t5")).next == ("approval_gate",)

    # Reject with feedback
    await client.post(
        "/api/v1/chat/approve",
        json={
            "thread_id": "t5",
            "approved": False,
            "feedback": "Assign task to dev02 instead",
        },
    )

    state = await get_state("t5")
    assert state.next == ()
    assert state.values["verification_outcome"] == "completed"
    assert state.values["completed_steps"][0].step_id == "s2"
    assert state.values["completed_steps"][0].output["assignee"] == "dev02"


@pytest.mark.asyncio
async def test_e2e_multi_step_sequential_workflow(e2e_env):
    """6. Multi-step plan executes sequentially and records all step results."""
    client, get_state, mock_planner, mock_tool = e2e_env
    mock_planner.return_value = make_plan(
        [
            make_step(
                "s1",
                "check_calendar_availability",
                CheckCalendarArgs(user_id="dev01", date="2026-11-20"),
            ),
            make_step(
                "s2",
                "create_task",
                CreateTaskArgs(title="Sprint planning", assignee="dev01"),
                deps=["s1"],
            ),
        ]
    )

    async def tool_dispatch(step, thread_id, session):
        return (
            {"slot": "10:00"}
            if step.tool == "check_calendar_availability"
            else {"task_id": "TASK-303"}
        )

    mock_tool.side_effect = tool_dispatch

    res = await client.post(
        "/api/v1/chat",
        json={"message": "Plan meeting and task", "thread_id": "t6"},
    )
    assert res.status_code == 200

    state = await get_state("t6")
    assert state.next == ()
    assert state.values["current_step_index"] == 2
    assert state.values["verification_outcome"] == "completed"
    assert [s.step_id for s in state.values["completed_steps"]] == ["s1", "s2"]


@pytest.mark.asyncio
async def test_e2e_transient_error_recovers_with_retry(e2e_env):
    """7. Transient network glitch triggers automatic retry and succeeds."""
    client, get_state, mock_planner, mock_tool = e2e_env
    mock_planner.return_value = make_plan(
        [
            make_step(
                "s1",
                "create_task",
                CreateTaskArgs(title="Deploy app", assignee="dev01"),
            )
        ]
    )
    mock_tool.side_effect = [
        ConnectionError("Database timeout"),
        {"task_id": "TASK-OK"},
    ]

    res = await client.post(
        "/api/v1/chat", json={"message": "Deploy app", "thread_id": "t7"}
    )
    assert res.status_code == 200

    state = await get_state("t7")
    assert state.next == ()
    assert mock_tool.call_count == 2
    assert state.values["retry_count"] == 0
    assert state.values["verification_outcome"] == "completed"
    assert state.values["completed_steps"][0].output == {"task_id": "TASK-OK"}


@pytest.mark.asyncio
async def test_e2e_transient_error_exhausted_retries_escalation(e2e_env):
    """8. Persistent transient errors exceed retry limit and escalate."""
    client, get_state, mock_planner, mock_tool = e2e_env
    mock_planner.return_value = make_plan(
        [
            make_step(
                "s1",
                "create_task",
                CreateTaskArgs(title="Sync data", assignee="dev01"),
            )
        ]
    )
    mock_tool.side_effect = TimeoutError("Network unreachable")

    res = await client.post(
        "/api/v1/chat", json={"message": "Sync data", "thread_id": "t8"}
    )
    assert res.status_code == 200

    state = await get_state("t8")
    assert state.next == ()
    assert state.values["verification_outcome"] == "escalate"
    assert state.values["retry_count"] == 3
    assert state.values["last_step_result"].success is False
    assert len(state.values.get("completed_steps", [])) == 0


@pytest.mark.asyncio
async def test_e2e_logical_tool_error_triggers_replan(e2e_env):
    """9. Business logic error triggers autonomous replanning and recovery."""
    client, get_state, mock_planner, mock_tool = e2e_env
    bad_plan = make_plan(
        [
            make_step(
                "s1",
                "create_task",
                CreateTaskArgs(title="Task", assignee="dev_inactive"),
            )
        ]
    )
    good_plan = make_plan(
        [
            make_step(
                "s2",
                "create_task",
                CreateTaskArgs(title="Task", assignee="dev01"),
            )
        ]
    )

    mock_planner.side_effect = (
        lambda msgs: good_plan
        if any("[PREVIOUS FAILURE TO REVISE]" in m.content for m in msgs)
        else bad_plan
    )

    async def tool_mock(step, thread_id, session):
        if step.args.assignee == "dev_inactive":
            raise ValueError("Assignee inactive")
        return {"task_id": "TASK-RECOVERED"}

    mock_tool.side_effect = tool_mock

    res = await client.post(
        "/api/v1/chat", json={"message": "Assign work", "thread_id": "t9"}
    )
    assert res.status_code == 200

    state = await get_state("t9")
    assert state.next == ()
    assert state.values["verification_outcome"] == "completed"
    assert state.values["completed_steps"][0].step_id == "s2"
    assert state.values["completed_steps"][0].output == {
        "task_id": "TASK-RECOVERED"
    }


@pytest.mark.asyncio
async def test_e2e_bulk_update_security_policy_enforcement(e2e_env):
    """10. Bulk update triggers security approval gate and completes once approved."""
    client, get_state, mock_planner, mock_tool = e2e_env
    mock_planner.return_value = make_plan(
        [
            make_step(
                "s1",
                "update_task",
                UpdateTaskArgs(
                    task_id="T-ALL", fields={"status": "Closed", "bulk": True}
                ),
            )
        ]
    )
    mock_tool.return_value = {"updated": True}

    # Pauses at approval gate because bulk is detected
    await client.post(
        "/api/v1/chat", json={"message": "Bulk close tasks", "thread_id": "t10"}
    )
    state = await get_state("t10")
    assert state.next == ("approval_gate",)
    assert state.values["requires_approval"] is True
    mock_tool.assert_not_called()

    # User approves
    res = await client.post(
        "/api/v1/chat/approve", json={"thread_id": "t10", "approved": True}
    )
    assert res.status_code == 200

    state = await get_state("t10")
    assert state.next == ()
    assert state.values["verification_outcome"] == "completed"
    assert state.values["completed_steps"][0].output == {"updated": True}
