"""SQLAlchemy models."""

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""


class TeamMember(Base):
    """A member of the team."""

    __tablename__ = "team_members"
    __table_args__ = (sa.UniqueConstraint("user_id", name="uq_team_members_user_id"),)

    id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.Identity(always=True), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(sa.String(50))
    full_name: Mapped[str] = mapped_column(sa.String(150))
    role: Mapped[str] = mapped_column(sa.String(100))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()")
    )


class Task(Base):
    """A task tracked by the workflow agent."""

    __tablename__ = "tasks"
    __table_args__ = (
        sa.CheckConstraint(
            "status IN ('open', 'in_progress', 'blocked', 'completed', 'cancelled')",
            name="ck_tasks_status",
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'urgent')",
            name="ck_tasks_priority",
        ),
        sa.UniqueConstraint("external_id", name="uq_tasks_external_id"),
    )

    id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.Identity(always=True), primary_key=True
    )
    external_id: Mapped[str] = mapped_column(sa.String(50))
    title: Mapped[str] = mapped_column(sa.String(255))
    assignee_id: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("team_members.id", name="fk_tasks_assignee_id_team_members"),
    )
    status: Mapped[str] = mapped_column(sa.String(20), server_default=sa.text("'open'"))
    priority: Mapped[str] = mapped_column(
        sa.String(20), server_default=sa.text("'medium'")
    )
    due_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()")
    )


class WorkflowExecution(Base):
    """A single run of the agentic workflow."""

    __tablename__ = "workflow_executions"
    __table_args__ = (
        sa.CheckConstraint(
            "status IN ('pending', 'planning', 'running', 'completed', "
            "'failed', 'awaiting_approval', 'rejected', 'cancelled')",
            name="ck_workflow_executions_status",
        ),
        sa.UniqueConstraint("thread_id", name="uq_workflow_executions_thread_id"),
    )

    id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.Identity(always=True), primary_key=True
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(postgresql.UUID(as_uuid=True))
    user_request: Mapped[str] = mapped_column(sa.Text)
    status: Mapped[str] = mapped_column(
        sa.String(20), server_default=sa.text("'pending'")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()")
    )


class PlanStep(Base):
    """A single step in a workflow execution plan."""

    __tablename__ = "plan_steps"
    __table_args__ = (
        sa.CheckConstraint(
            "step_number > 0", name="ck_plan_steps_step_number_positive"
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', "
            "'skipped', 'awaiting_approval')",
            name="ck_plan_steps_status",
        ),
        sa.UniqueConstraint(
            "workflow_execution_id",
            "step_number",
            name="uq_plan_steps_workflow_execution_id_step_number",
        ),
    )

    id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.Identity(always=True), primary_key=True
    )
    workflow_execution_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey(
            "workflow_executions.id",
            name="fk_plan_steps_workflow_execution_id_workflow_executions",
            ondelete="CASCADE",
        ),
    )
    step_number: Mapped[int] = mapped_column(sa.Integer)
    description: Mapped[str] = mapped_column(sa.Text)
    tool_name: Mapped[str | None] = mapped_column(sa.String(100))
    input_data: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, server_default=sa.text("'{}'::jsonb")
    )
    depends_on_step_numbers: Mapped[list[int]] = mapped_column(
        postgresql.ARRAY(sa.Integer), server_default=sa.text("'{}'::integer[]")
    )
    status: Mapped[str] = mapped_column(
        sa.String(20), server_default=sa.text("'pending'")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()")
    )
