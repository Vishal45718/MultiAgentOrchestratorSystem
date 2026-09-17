"""User repository — CRUD and domain queries for the User model."""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import User
from src.db.repositories.base import BaseRepository, NotFoundError


class UserRepository(BaseRepository[User]):
    """Data-access layer for :class:`~src.db.models.User`."""

    model_class = User

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    def create(
        self,
        session: Session,
        *,
        email: str,
        name: Optional[str] = None,
        is_active: bool = True,
    ) -> User:
        """Instantiate and add a new User to the session.

        The caller must flush/commit to persist.
        """
        user = User(email=email, name=name, is_active=is_active)
        return self.add(session, user)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_by_email(self, session: Session, email: str) -> User:
        """Return the user with the given email or raise :class:`NotFoundError`."""
        stmt = select(User).where(User.email == email)
        obj = session.scalars(stmt).first()
        if obj is None:
            raise NotFoundError(User.__name__, email)
        return obj

    def get_by_email_optional(self, session: Session, email: str) -> Optional[User]:
        """Return the user with the given email or ``None``."""
        stmt = select(User).where(User.email == email)
        return session.scalars(stmt).first()

    def list_active(
        self, session: Session, limit: int = 100, offset: int = 0
    ) -> list[User]:
        """Return paginated list of active users."""
        stmt = (
            select(User)
            .where(User.is_active.is_(True))
            .order_by(User.created_at)
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(stmt).all())

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(
        self,
        session: Session,
        user_id: uuid.UUID,
        *,
        name: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> User:
        """Apply field updates to an existing User and return it.

        Only non-``None`` keyword arguments are applied.
        """
        user = self.get_by_id(session, user_id)
        if name is not None:
            user.name = name
        if is_active is not None:
            user.is_active = is_active
        return user
