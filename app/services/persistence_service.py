"""Database persistence for idempotency ledger and workflow execution status."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config.db_config import get_sync_engine
from app.models import Base, IdempotencyLedger, WorkflowExecution


def _to_uuid(val: Any) -> uuid.UUID:
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except (ValueError, TypeError, AttributeError):
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(val))


def get_idempotency_record(key: str, engine=None) -> Any | None:
    """Retrieve cached step result from idempotency ledger."""
    eng = engine or get_sync_engine()
    Base.metadata.create_all(eng)
    with Session(eng) as session:
        record = session.get(IdempotencyLedger, key)
        return record.result if record else None


def save_idempotency_record(
    key: str,
    step_id: str | None,
    tool_name: str | None,
    result: Any,
    status: str = "completed",
    engine=None,
) -> None:
    """Persist step result to idempotency ledger."""
    eng = engine or get_sync_engine()
    Base.metadata.create_all(eng)
    with Session(eng) as session:
        record = session.get(IdempotencyLedger, key)
        if record:
            record.result = result
            record.status = status
            record.step_id = step_id
            record.tool_name = tool_name
            record.updated_at = datetime.now(timezone.utc)
        else:
            session.add(
                IdempotencyLedger(
                    key=key,
                    step_id=step_id,
                    tool_name=tool_name,
                    result=result,
                    status=status,
                    updated_at=datetime.now(timezone.utc),
                )
            )
        session.commit()


def update_workflow_status(
    thread_id: str | uuid.UUID,
    status: str,
    user_request: str = "",
    engine=None,
) -> None:
    """Persist workflow execution status across process restarts."""
    eng = engine or get_sync_engine()
    Base.metadata.create_all(eng)
    uid = _to_uuid(thread_id)
    with Session(eng) as session:
        record = session.scalar(
            select(WorkflowExecution).where(WorkflowExecution.thread_id == uid)
        )
        if record:
            record.status = status
            record.updated_at = datetime.now(timezone.utc)
            if user_request and not record.user_request:
                record.user_request = user_request
        else:
            session.add(
                WorkflowExecution(
                    thread_id=uid,
                    status=status,
                    user_request=user_request or "Workflow Execution",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            )
        session.commit()


def get_workflow_status(
    thread_id: str | uuid.UUID,
    engine=None,
) -> str | None:
    """Get current workflow execution status by thread ID."""
    eng = engine or get_sync_engine()
    Base.metadata.create_all(eng)
    uid = _to_uuid(thread_id)
    with Session(eng) as session:
        record = session.scalar(
            select(WorkflowExecution).where(WorkflowExecution.thread_id == uid)
        )
        return record.status if record else None


def clear_idempotency_ledger(engine=None) -> None:
    """Clear all records from idempotency ledger and workflow executions."""
    eng = engine or get_sync_engine()
    Base.metadata.create_all(eng)
    with Session(eng) as session:
        session.execute(delete(IdempotencyLedger))
        session.execute(delete(WorkflowExecution))
        session.commit()
