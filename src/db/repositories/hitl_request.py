"""HITLRequest repository — CRUD and domain queries for the HITLRequest model."""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import HITLRequest, HITLStatus
from src.db.repositories.base import BaseRepository


class HITLRequestRepository(BaseRepository[HITLRequest]):
    """Data-access layer for :class:`~src.db.models.HITLRequest`."""

    model_class = HITLRequest

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    def create(
        self,
        session: Session,
        *,
        task_id: uuid.UUID,
        reason: str,
        run_id: Optional[uuid.UUID] = None,
        context_data: Optional[dict[str, Any]] = None,
        status: HITLStatus = HITLStatus.PENDING,
    ) -> HITLRequest:
        """Instantiate and add a new HITLRequest to the session."""
        hitl = HITLRequest(
            task_id=task_id,
            run_id=run_id,
            reason=reason,
            context_data=context_data,
            status=status,
        )
        return self.add(session, hitl)

    # ------------------------------------------------------------------
    # Retrieval / filtering
    # ------------------------------------------------------------------

    def list_pending(
        self,
        session: Session,
        limit: int = 50,
        offset: int = 0,
    ) -> list[HITLRequest]:
        """Return all PENDING HITL requests, ordered oldest-first (review queue)."""
        stmt = (
            select(HITLRequest)
            .where(HITLRequest.status == HITLStatus.PENDING)
            .order_by(HITLRequest.created_at)
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(stmt).all())

    def list_by_task(
        self,
        session: Session,
        task_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[HITLRequest]:
        """Return all HITL requests for a task, ordered by creation time."""
        stmt = (
            select(HITLRequest)
            .where(HITLRequest.task_id == task_id)
            .order_by(HITLRequest.created_at)
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(stmt).all())

    def get_pending_for_task(
        self, session: Session, task_id: uuid.UUID
    ) -> Optional[HITLRequest]:
        """Return the first PENDING HITL request for a task, or ``None``."""
        stmt = (
            select(HITLRequest)
            .where(
                HITLRequest.task_id == task_id,
                HITLRequest.status == HITLStatus.PENDING,
            )
            .order_by(HITLRequest.created_at)
            .limit(1)
        )
        return session.scalars(stmt).first()

    # ------------------------------------------------------------------
    # Update / Decision recording
    # ------------------------------------------------------------------

    def record_decision(
        self,
        session: Session,
        hitl_id: uuid.UUID,
        *,
        decision: HITLStatus,
        decided_by_id: Optional[uuid.UUID] = None,
        decision_payload: Optional[dict[str, Any]] = None,
    ) -> HITLRequest:
        """Record a human decision on a HITL request.

        Sets ``status`` and ``decision`` to the same ``decision`` value,
        records who decided and when, and stores any payload.
        """
        hitl = self.get_by_id(session, hitl_id)
        hitl.status = decision
        hitl.decision = decision
        hitl.decided_at = datetime.now(timezone.utc)
        if decided_by_id is not None:
            hitl.decided_by_id = decided_by_id
        if decision_payload is not None:
            hitl.decision_payload = decision_payload
        return hitl
