from unittest.mock import MagicMock

from langchain_core.embeddings import FakeEmbeddings
from qdrant_client import QdrantClient

from app.agents.workflow_agent import (
    create_workflow_graph,
    generate_plan,
)
from app.schemas.workflow import AgentState, ExecutionPlan, PlanStep
from app.services.core_services.sop_service import (
    ingest_sops,
    search_workflow_templates,
    split_sops_by_headings,
)


def _sample_steps() -> list[PlanStep]:
    return [
        PlanStep(
            step_id="step_1",
            action="Check calendar",
            tool_name="check_calendar_availability",
        ),
        PlanStep(step_id="step_2", action="Create task", tool_name="create_task"),
        PlanStep(step_id="step_3", action="Update task", tool_name="update_task"),
        PlanStep(step_id="step_4", action="Notify PM", tool_name="send_notification"),
    ]


def test_sop_splitting_and_metadata():
    """Verify workflow_sops.md splits into 10 sections with accurate metadata."""
    from pathlib import Path

    sop_path = Path("app/data/workflow_sops.md")
    content = sop_path.read_text(encoding="utf-8")
    docs = split_sops_by_headings(content)

    assert len(docs) == 10

    by_num = {
        d.metadata["section_number"]: d for d in docs if "section_number" in d.metadata
    }
    assert by_num[2].metadata["workflow_type"] == "task"
    assert by_num[2].metadata["action_type"] == "create_task"

    assert by_num[4].metadata["workflow_type"] == "notification"
    assert by_num[4].metadata["action_type"] == "send_notification"

    assert by_num[5].metadata["workflow_type"] == "task"
    assert by_num[5].metadata["action_type"] == "update_task"


def test_sop_ingestion_and_metadata_filtered_retrieval():
    """Verify Qdrant ingestion and filtered semantic retrieval by metadata."""
    client = QdrantClient(":memory:")
    embeddings = FakeEmbeddings(size=4)
    collection = "test_workflow_sops"

    ingested = ingest_sops(
        collection_name=collection,
        client=client,
        embeddings=embeddings,
    )
    assert len(ingested) == 10

    # Retrieve with workflow_type filter
    task_sops = search_workflow_templates(
        query="manage tasks",
        workflow_type="task",
        collection_name=collection,
        client=client,
        embeddings=embeddings,
    )
    assert len(task_sops) > 0
    assert all(sop["workflow_type"] == "task" for sop in task_sops)

    # Retrieve with both workflow_type and action_type filters
    update_sops = search_workflow_templates(
        query="bulk update tasks",
        workflow_type="task",
        action_type="update_task",
        collection_name=collection,
        client=client,
        embeddings=embeddings,
    )
    assert len(update_sops) == 1
    assert update_sops[0]["action_type"] == "update_task"


def test_generate_plan_uses_retrieved_sops():
    """Verify generate_plan injects retrieved SOP guidelines into LLM prompt."""
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = ExecutionPlan(
        goal="Create API review", steps=_sample_steps()
    )

    state: AgentState = {
        "parsed_goal": "Create API review",
        "retrieved_sops": [
            {
                "content": "Check team directory before creating task.",
                "workflow_type": "task",
                "action_type": "create_task",
            }
        ],
    }

    result = generate_plan(state, llm=mock_llm)
    assert "plan" in result

    # Check prompt passed to LLM
    invoke_call = mock_llm.with_structured_output.return_value.invoke.call_args
    messages = invoke_call[0][0]
    user_message = next(msg[1] for msg in messages if msg[0] == "user")
    assert "Relevant SOP Guidelines:" in user_message
    assert "Check team directory before creating task." in user_message


def test_workflow_graph_with_retrieval_node():
    """Verify workflow graph executes parse_goal -> retrieve_sops -> generate_plan."""
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = ExecutionPlan(
        goal="Create an API review task", steps=_sample_steps()
    )

    mock_sops = [
        {
            "content": "Every task must have a concise title and assignee.",
            "workflow_type": "task",
            "action_type": "create_task",
        }
    ]
    mock_retriever = MagicMock(return_value=mock_sops)

    graph = create_workflow_graph(llm=mock_llm, retriever_fn=mock_retriever)
    result = graph.invoke({"user_request": "Create an API review task"})

    assert result["parsed_goal"] == "Create an API review task"
    mock_retriever.assert_called_once_with("Create an API review task")
    assert result["retrieved_sops"] == mock_sops
    assert len(result["plan"]) == 4
