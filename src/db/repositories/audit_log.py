"""AuditLog repository — append-only write and query operations."""

import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import AuditLog
from src.db.repositories.base import BaseRepository, NotFoundError


class AuditLogRepository(BaseRepository[AuditLog]):
    """Data-access layer for :class:`~src.db.models.AuditLog`.

    The audit log is intentionally append-only: there is no ``update``
    or ``delete`` method.  ``get_by_id`` is provided for verification;
    deleting an audit record is an explicit error.
    """

    model_class = AuditLog

    # ------------------------------------------------------------------
    # Creation (append-only)
    # ------------------------------------------------------------------

    def create(
        self,
        session: Session,
        *,
        event_type: str,
        entity_type: str,
        entity_id: str,
        task_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> AuditLog:
        """Append a new audit log entry to the session."""
        log = AuditLog(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            task_id=task_id,
            user_id=user_id,
            details=details,
        )
        return self.add(session, log)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_by_id(self, session: Session, entity_id: uuid.UUID) -> AuditLog:
        """Return the audit log entry or raise :class:`NotFoundError`."""
        obj = session.get(AuditLog, entity_id)
        if obj is None:
            raise NotFoundError(AuditLog.__name__, entity_id)
        return obj

    def list_by_task(
        self,
        session: Session,
        task_id: uuid.UUID,
        limit: int = 200,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Return audit entries for a task, ordered by creation time."""
        stmt = (
            select(AuditLog)
            .where(AuditLog.task_id == task_id)
            .order_by(AuditLog.created_at)
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(stmt).all())

    def list_by_entity(
        self,
        session: Session,
        entity_type: str,
        entity_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Return audit entries for a specific entity type and ID."""
        stmt = (
            select(AuditLog)
            .where(
                AuditLog.entity_type == entity_type,
                AuditLog.entity_id == entity_id,
            )
            .order_by(AuditLog.created_at)
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(stmt).all())

    def list_by_event_type(
        self,
        session: Session,
        event_type: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Return audit entries filtered by event type."""
        stmt = (
            select(AuditLog)
            .where(AuditLog.event_type == event_type)
            .order_by(AuditLog.created_at.desc())
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
    ) -> list[AuditLog]:
        """Return audit entries attributed to a specific user."""
        stmt = (
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(stmt).all())

    # ------------------------------------------------------------------
    # Intentionally NO update/delete — audit log is immutable
    # ------------------------------------------------------------------
