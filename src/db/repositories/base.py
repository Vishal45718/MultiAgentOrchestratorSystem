"""Base repository helpers shared by all concrete repositories."""

import uuid
from typing import Any, Generic, Optional, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import Base

ModelT = TypeVar("ModelT", bound=Base)


class NotFoundError(Exception):
    """Raised when a requested entity does not exist in the database.

    Attributes:
        model_name: Human-readable name of the model class.
        entity_id: The ID value that was looked up.
    """

    def __init__(self, model_name: str, entity_id: Any) -> None:
        self.model_name = model_name
        self.entity_id = entity_id
        super().__init__(f"{model_name} with id={entity_id!r} not found.")


class BaseRepository(Generic[ModelT]):
    """Generic base repository providing common CRUD operations.

    Sub-classes set the ``model_class`` class attribute to their domain model.

    All methods accept a ``session`` parameter — transaction boundaries are
    the caller's responsibility.  Repositories *never* call
    ``session.commit()``.
    """

    model_class: type[ModelT]

    # ------------------------------------------------------------------
    # Core helpers
    # ------------------------------------------------------------------

    def get_by_id(self, session: Session, entity_id: uuid.UUID) -> ModelT:
        """Return the entity or raise :class:`NotFoundError`."""
        obj = session.get(self.model_class, entity_id)
        if obj is None:
            raise NotFoundError(self.model_class.__name__, entity_id)
        return obj

    def get_by_id_optional(
        self, session: Session, entity_id: uuid.UUID
    ) -> Optional[ModelT]:
        """Return the entity or ``None`` if it does not exist."""
        return session.get(self.model_class, entity_id)

    def list_all(
        self, session: Session, limit: int = 100, offset: int = 0
    ) -> list[ModelT]:
        """Return a paginated list of all entities (unfiltered)."""
        stmt = (
            select(self.model_class)
            .order_by(self.model_class.id)  # type: ignore[arg-type]
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(stmt).all())

    def add(self, session: Session, obj: ModelT) -> ModelT:
        """Add the object to the session (not yet flushed or committed)."""
        session.add(obj)
        return obj

    def delete(self, session: Session, obj: ModelT) -> None:
        """Mark the object for deletion (not yet committed)."""
        session.delete(obj)
