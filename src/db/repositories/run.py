"""Run repository — CRUD and domain queries for the Run model."""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import Run, RunStatus
from src.db.repositories.base import BaseRepository


class RunRepository(BaseRepository[Run]):
    """Data-access layer for :class:`~src.db.models.Run`."""

    model_class = Run

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    def create(
        self,
        session: Session,
        *,
        task_id: uuid.UUID,
        status: RunStatus = RunStatus.PENDING,
        celery_task_id: Optional[str] = None,
        checkpoint_id: Optional[str] = None,
        current_node: Optional[str] = None,
    ) -> Run:
        """Instantiate and add a new Run to the session."""
        run = Run(
            task_id=task_id,
            status=status,
            celery_task_id=celery_task_id,
            checkpoint_id=checkpoint_id,
            current_node=current_node,
        )
        return self.add(session, run)

    # ------------------------------------------------------------------
    # Retrieval / filtering
    # ------------------------------------------------------------------

    def list_by_task(
        self,
        session: Session,
        task_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Run]:
        """Return all runs for a task, ordered by creation time ascending."""
        stmt = (
            select(Run)
            .where(Run.task_id == task_id)
            .order_by(Run.created_at)
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(stmt).all())

    def get_latest_by_task(self, session: Session, task_id: uuid.UUID) -> Optional[Run]:
        """Return the most recently created Run for a task, or ``None``."""
        stmt = (
            select(Run)
            .where(Run.task_id == task_id)
            .order_by(Run.created_at.desc())
            .limit(1)
        )
        return session.scalars(stmt).first()

    def get_by_celery_task_id(
        self, session: Session, celery_task_id: str
    ) -> Optional[Run]:
        """Return the Run associated with a Celery task ID, or ``None``."""
        stmt = select(Run).where(Run.celery_task_id == celery_task_id)
        return session.scalars(stmt).first()

    def list_by_status(
        self,
        session: Session,
        status: RunStatus,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Run]:
        """Return runs in the given status, ordered by creation time."""
        stmt = (
            select(Run)
            .where(Run.status == status)
            .order_by(Run.created_at)
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
        run_id: uuid.UUID,
        status: RunStatus,
        *,
        current_node: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Run:
        """Transition a run's status and optionally update current node."""
        run = self.get_by_id(session, run_id)
        run.status = status
        if current_node is not None:
            run.current_node = current_node
        if error_message is not None:
            run.error_message = error_message
        return run

    def mark_started(
        self,
        session: Session,
        run_id: uuid.UUID,
        *,
        celery_task_id: Optional[str] = None,
        current_node: Optional[str] = None,
    ) -> Run:
        """Mark a run as RUNNING and set its start time."""
        run = self.get_by_id(session, run_id)
        run.status = RunStatus.RUNNING
        run.started_at = datetime.now(timezone.utc)
        if celery_task_id is not None:
            run.celery_task_id = celery_task_id
        if current_node is not None:
            run.current_node = current_node
        return run

    def mark_completed(
        self,
        session: Session,
        run_id: uuid.UUID,
        status: RunStatus = RunStatus.COMPLETED,
        *,
        error_message: Optional[str] = None,
        state_snapshot: Optional[dict[str, Any]] = None,
    ) -> Run:
        """Mark a run as completed/failed/escalated and set its end time."""
        run = self.get_by_id(session, run_id)
        run.status = status
        run.completed_at = datetime.now(timezone.utc)
        if error_message is not None:
            run.error_message = error_message
        if state_snapshot is not None:
            run.state_snapshot = state_snapshot
        return run

    def increment_retry(self, session: Session, run_id: uuid.UUID) -> Run:
        """Increment the retry count of a run by 1."""
        run = self.get_by_id(session, run_id)
        run.retry_count += 1
        return run

    def set_checkpoint(
        self,
        session: Session,
        run_id: uuid.UUID,
        checkpoint_id: str,
        state_snapshot: Optional[dict[str, Any]] = None,
    ) -> Run:
        """Store the latest checkpoint ID (and optional state snapshot)."""
        run = self.get_by_id(session, run_id)
        run.checkpoint_id = checkpoint_id
        if state_snapshot is not None:
            run.state_snapshot = state_snapshot
        return run
