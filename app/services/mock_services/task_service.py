from datetime import datetime, timezone
from typing import Any

from app.models.mock_models import Task, TeamMember
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

VALID_PRIORITIES = {"Lowest", "Low", "Medium", "High", "Highest"}


def task_to_dict(task: Task) -> dict[str, Any]:
    return {
        "task_id": task.task_id,
        "title": task.title,
        "description": task.description,
        "assignee": task.assignee,
        "reporter": task.reporter,
        "status": task.status,
        "priority": task.priority,
        "created_at": task.created_at,
        "due_date": task.due_date,
        "labels": task.labels or [],
        "project": task.project,
        "idempotency_key": task.idempotency_key,
    }


class TaskService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_task(
        self,
        title: str,
        assignee: str,
        priority: str = "Medium",
        description: str = "",
        project: str = "PLAT",
        due_date: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if idempotency_key:
            stmt = select(Task).where(Task.idempotency_key == idempotency_key)
            existing = await self.session.scalar(stmt)
            if existing:
                return task_to_dict(existing)

        member = await self.session.get(TeamMember, assignee)
        if not member or not member.active:
            raise ValueError(f"Assignee '{assignee}' is not an active team member")

        if priority not in VALID_PRIORITIES:
            raise ValueError(
                f"Invalid priority '{priority}'. Must be one of {VALID_PRIORITIES}"
            )

        stmt = select(Task.task_id).order_by(Task.task_id.desc()).limit(1)
        latest_id = await self.session.scalar(stmt)
        if (
            latest_id
            and latest_id.startswith("TASK-")
            and latest_id.split("-")[1].isdigit()
        ):
            next_num = int(latest_id.split("-")[1]) + 1
        else:
            next_num = 101
        new_task_id = f"TASK-{next_num}"

        task = Task(
            task_id=new_task_id,
            title=title,
            description=description,
            assignee=assignee,
            reporter="pm01",
            status="Open",
            priority=priority,
            created_at=datetime.now(timezone.utc).isoformat(),
            due_date=due_date,
            project=project,
            idempotency_key=idempotency_key,
        )
        self.session.add(task)
        await self.session.commit()
        return task_to_dict(task)

    async def get_task(self, task_id: str) -> dict[str, Any] | None:
        task = await self.session.get(Task, task_id)
        return task_to_dict(task) if task else None

    async def update_task(self, task_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        task = await self.session.get(Task, task_id)
        if not task:
            raise ValueError(f"Task '{task_id}' not found")

        if "assignee" in fields:
            member = await self.session.get(TeamMember, fields["assignee"])
            if not member or not member.active:
                raise ValueError(
                    f"Assignee '{fields['assignee']}' is not an active team member"
                )

        if "priority" in fields and fields["priority"] not in VALID_PRIORITIES:
            raise ValueError(f"Invalid priority '{fields['priority']}'")

        for key, value in fields.items():
            if hasattr(task, key):
                setattr(task, key, value)

        await self.session.commit()
        return task_to_dict(task)

    async def list_tasks(
        self,
        status: str | None = None,
        priority: str | None = None,
        is_overdue: bool | None = None,
        reference_date: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        stmt = select(Task)
        if status:
            stmt = stmt.where(Task.status == status)
        if priority:
            stmt = stmt.where(Task.priority == priority)

        if is_overdue is not None:
            ref = reference_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
            if is_overdue:
                stmt = stmt.where(Task.due_date < ref, Task.status != "Done")
            else:
                stmt = stmt.where((Task.due_date >= ref) | (Task.status == "Done"))

        stmt = stmt.limit(limit)
        tasks = (await self.session.scalars(stmt)).all()
        return [task_to_dict(t) for t in tasks]
