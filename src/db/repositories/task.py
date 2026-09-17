"""Task repository — CRUD and domain queries for the Task model."""

import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import Task, TaskStatus
from src.db.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    """Data-access layer for :class:`~src.db.models.Task`."""

    model_class = Task

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    def create(
        self,
        session: Session,
        *,
        input_data: dict[str, Any],
        title: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
        status: TaskStatus = TaskStatus.QUEUED,
        task_metadata: Optional[dict[str, Any]] = None,
    ) -> Task:
        """Instantiate and add a new Task to the session.

        The caller must flush/commit to persist.
        """
        task = Task(
            title=title,
            user_id=user_id,
            input_data=input_data,
            status=status,
            task_metadata=task_metadata or {},
        )
        return self.add(session, task)

    # ------------------------------------------------------------------
    # Retrieval / filtering
    # ------------------------------------------------------------------

    def list_by_status(
        self,
        session: Session,
        status: TaskStatus,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Task]:
        """Return tasks with the given status, ordered by creation time."""
        stmt = (
            select(Task)
            .where(Task.status == status)
            .order_by(Task.created_at)
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(stmt).all())

    def list_by_user(
        self,
        session: Session,
        user_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Task]:
        """Return all tasks belonging to a specific user."""
        stmt = (
            select(Task)
            .where(Task.user_id == user_id)
            .order_by(Task.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(stmt).all())

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update_status(
        self,
        session: Session,
        task_id: uuid.UUID,
        status: TaskStatus,
        *,
        current_step: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Task:
        """Transition a task's status.

        Optionally updates ``current_step`` and ``error_message``.
        """
        task = self.get_by_id(session, task_id)
        task.status = status
        if current_step is not None:
            task.current_step = current_step
        if error_message is not None:
            task.error_message = error_message
        return task

    def set_result(
        self,
        session: Session,
        task_id: uuid.UUID,
        result: dict[str, Any],
        status: TaskStatus = TaskStatus.COMPLETED,
    ) -> Task:
        """Store the final result and mark the task completed (or given status)."""
        task = self.get_by_id(session, task_id)
        task.result = result
        task.status = status
        return task

    def update(
        self,
        session: Session,
        task_id: uuid.UUID,
        *,
        title: Optional[str] = None,
        current_step: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        error_message: Optional[str] = None,
        result: Optional[dict[str, Any]] = None,
        task_metadata: Optional[dict[str, Any]] = None,
    ) -> Task:
        """Apply arbitrary field updates to an existing Task and return it."""
        task = self.get_by_id(session, task_id)
        if title is not None:
            task.title = title
        if current_step is not None:
            task.current_step = current_step
        if status is not None:
            task.status = status
        if error_message is not None:
            task.error_message = error_message
        if result is not None:
            task.result = result
        if task_metadata is not None:
            task.task_metadata = task_metadata
        return task
