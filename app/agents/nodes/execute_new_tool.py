from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.env_config import get_settings
from app.config.postgres_config import async_session_factory
from app.repository.vector_repository.qdrant_repository import get_qdrant_repository
from app.schemas.state import Plan, Step, WorkflowState
from app.services.core_services.embedding_service import get_embedding_provider
from app.services.core_services.sop_service import search_sops
from app.services.mock_services import CalendarService, NotificationService, TaskService

async def _run_tool(step: Step, thread_id: str, session: AsyncSession) -> Any:
    """Dispatches the step to the appropriate service."""
    idempotency_key = f"{thread_id}:{step.step_id}"
    args: Any = step.args
    
    match step.tool:
        case "create_task":
            service = TaskService(session)
            return await service.create_task(
                title=args.title,
                assignee=args.assignee,
                priority=args.priority,
                idempotency_key=idempotency_key,
            )
        case "update_task":
            service = TaskService(session)
            return await service.update_task(
                task_id=args.task_id,
                fields=args.fields,
            )
        case "send_notification":
            service = NotificationService(session)
            return await service.send_notification(
                recipient=args.recipient,
                message=args.message,
                idempotency_key=idempotency_key,
            )
        case "check_calendar_availability":
            service = CalendarService(session)
            return await service.check_availability(
                user_id=args.user_id,
                date_str=args.date,
            )
        case "search_workflow_templates":
            return search_sops(
                repository=get_qdrant_repository(),
                embedding_provider=get_embedding_provider(),
                collection_name=get_settings().QDRANT_COLLECTION,
                query=args.query,
            )

async def execute_next_tool(state: WorkflowState):
    """LangGraph node to execute the current step tool."""

    plan: Plan | None = state.get("plan")
    current_index = state.get("current_step_index", 0)

    if not plan or current_index >= len(plan.steps):
        return {"last_step_result": None}

    step = plan.steps[current_index]
    thread_id = state.get("thread_id", "default")

    try:
        async with async_session_factory() as session:
            output = await _run_tool(step, thread_id, session)
        return {
            "last_step_result": {
                "step_id": step.step_id,
                "tool": step.tool,
                "success": True,
                "output": output,
                "error": None,
            }
        }
    except Exception as e:
        return {
            "last_step_result": {
                "step_id": step.step_id,
                "tool": step.tool,
                "success": False,
                "output": None,
                "error": str(e),
            }
        }