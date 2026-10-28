"""SQL repositories for persisted entities."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PlanStep, Task, TeamMember, WorkflowExecution


class TeamMemberRepository:
    """Data access for team members."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all(self) -> list[TeamMember]:
        """Return every team member."""
        result = await self._session.execute(select(TeamMember))
        return list(result.scalars().all())


class TaskRepository:
    """Data access for tasks."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all(self) -> list[Task]:
        """Return every task."""
        result = await self._session.execute(select(Task))
        return list(result.scalars().all())


class WorkflowExecutionRepository:
    """Data access for workflow executions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all(self) -> list[WorkflowExecution]:
        """Return every workflow execution."""
        result = await self._session.execute(select(WorkflowExecution))
        return list(result.scalars().all())


class PlanStepRepository:
    """Data access for plan steps."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all(self) -> list[PlanStep]:
        """Return every plan step."""
        result = await self._session.execute(select(PlanStep))
        return list(result.scalars().all())
