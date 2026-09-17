"""Message repository — CRUD and domain queries for the Message model."""

import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import Message, MessageRole
from src.db.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    """Data-access layer for :class:`~src.db.models.Message`."""

    model_class = Message

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    def create(
        self,
        session: Session,
        *,
        task_id: uuid.UUID,
        role: MessageRole,
        content: str,
        run_id: Optional[uuid.UUID] = None,
        agent_role: Optional[str] = None,
        tokens: Optional[int] = None,
        msg_metadata: Optional[dict[str, Any]] = None,
    ) -> Message:
        """Instantiate and add a new Message to the session."""
        msg = Message(
            task_id=task_id,
            run_id=run_id,
            role=role,
            content=content,
            agent_role=agent_role,
            tokens=tokens,
            msg_metadata=msg_metadata or {},
        )
        return self.add(session, msg)

    # ------------------------------------------------------------------
    # Retrieval / filtering
    # ------------------------------------------------------------------

    def list_by_task(
        self,
        session: Session,
        task_id: uuid.UUID,
        limit: int = 200,
        offset: int = 0,
    ) -> list[Message]:
        """Return all messages for a task, ordered by creation time ascending."""
        stmt = (
            select(Message)
            .where(Message.task_id == task_id)
            .order_by(Message.created_at)
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
    ) -> list[Message]:
        """Return all messages for a run, ordered by creation time ascending."""
        stmt = (
            select(Message)
            .where(Message.run_id == run_id)
            .order_by(Message.created_at)
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(stmt).all())

    def list_by_role(
        self,
        session: Session,
        task_id: uuid.UUID,
        role: MessageRole,
        limit: int = 200,
        offset: int = 0,
    ) -> list[Message]:
        """Return messages for a task filtered by role."""
        stmt = (
            select(Message)
            .where(Message.task_id == task_id, Message.role == role)
            .order_by(Message.created_at)
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(stmt).all())
