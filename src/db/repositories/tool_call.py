"""ToolCall repository — CRUD and domain queries for the ToolCall model."""

import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import ToolCall, ToolCallStatus
from src.db.repositories.base import BaseRepository


class ToolCallRepository(BaseRepository[ToolCall]):
    """Data-access layer for :class:`~src.db.models.ToolCall`."""

    model_class = ToolCall

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    def create(
        self,
        session: Session,
        *,
        task_id: uuid.UUID,
        tool_name: str,
        input_arguments: dict[str, Any],
        run_id: Optional[uuid.UUID] = None,
        agent_role: Optional[str] = None,
        output_result: Optional[dict[str, Any]] = None,
        status: ToolCallStatus = ToolCallStatus.SUCCESS,
        duration_ms: Optional[float] = None,
        error_message: Optional[str] = None,
    ) -> ToolCall:
        """Instantiate and add a new ToolCall to the session."""
        tc = ToolCall(
            task_id=task_id,
            run_id=run_id,
            agent_role=agent_role,
            tool_name=tool_name,
            input_arguments=input_arguments,
            output_result=output_result,
            status=status,
            duration_ms=duration_ms,
            error_message=error_message,
        )
        return self.add(session, tc)

    # ------------------------------------------------------------------
    # Retrieval / filtering
    # ------------------------------------------------------------------

    def list_by_task(
        self,
        session: Session,
        task_id: uuid.UUID,
        limit: int = 200,
        offset: int = 0,
    ) -> list[ToolCall]:
        """Return all tool calls for a task, ordered by creation time."""
        stmt = (
            select(ToolCall)
            .where(ToolCall.task_id == task_id)
            .order_by(ToolCall.created_at)
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(stmt).all())

    def list_by_run(
        self,
        session: Session,
        run_id: uuid.UUID,
        limit: int = 200,
        offset: int = 0,
    ) -> list[ToolCall]:
        """Return all tool calls for a run, ordered by creation time."""
        stmt = (
            select(ToolCall)
            .where(ToolCall.run_id == run_id)
            .order_by(ToolCall.created_at)
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(stmt).all())

    def list_by_tool_name(
        self,
        session: Session,
        tool_name: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ToolCall]:
        """Return all calls to a named tool across all tasks."""
        stmt = (
            select(ToolCall)
            .where(ToolCall.tool_name == tool_name)
            .order_by(ToolCall.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(stmt).all())

    def list_by_status(
        self,
        session: Session,
        status: ToolCallStatus,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ToolCall]:
        """Return tool calls filtered by outcome status."""
        stmt = (
            select(ToolCall)
            .where(ToolCall.status == status)
            .order_by(ToolCall.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(stmt).all())

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def record_result(
        self,
        session: Session,
        tool_call_id: uuid.UUID,
        *,
        status: ToolCallStatus,
        output_result: Optional[dict[str, Any]] = None,
        error_message: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> ToolCall:
        """Update a tool call with its outcome after execution completes."""
        tc = self.get_by_id(session, tool_call_id)
        tc.status = status
        if output_result is not None:
            tc.output_result = output_result
        if error_message is not None:
            tc.error_message = error_message
        if duration_ms is not None:
            tc.duration_ms = duration_ms
        return tc
