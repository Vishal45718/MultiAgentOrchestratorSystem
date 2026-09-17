"""EvalResult repository — write and query operations for evaluation metrics."""

import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import EvalResult
from src.db.repositories.base import BaseRepository


class EvalResultRepository(BaseRepository[EvalResult]):
    """Data-access layer for :class:`~src.db.models.EvalResult`."""

    model_class = EvalResult

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    def create(
        self,
        session: Session,
        *,
        eval_run_id: str,
        dataset_name: str,
        scorer_name: str,
        score: float,
        task_id: Optional[uuid.UUID] = None,
        metrics: Optional[dict[str, Any]] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> EvalResult:
        """Instantiate and add a new EvalResult to the session."""
        result = EvalResult(
            eval_run_id=eval_run_id,
            dataset_name=dataset_name,
            task_id=task_id,
            scorer_name=scorer_name,
            score=score,
            metrics=metrics,
            details=details,
        )
        return self.add(session, result)

    # ------------------------------------------------------------------
    # Retrieval / filtering
    # ------------------------------------------------------------------

    def list_by_eval_run(
        self,
        session: Session,
        eval_run_id: str,
        limit: int = 500,
        offset: int = 0,
    ) -> list[EvalResult]:
        """Return all results for a specific evaluation run."""
        stmt = (
            select(EvalResult)
            .where(EvalResult.eval_run_id == eval_run_id)
            .order_by(EvalResult.created_at)
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
    ) -> list[EvalResult]:
        """Return all eval results linked to a task."""
        stmt = (
            select(EvalResult)
            .where(EvalResult.task_id == task_id)
            .order_by(EvalResult.created_at)
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(stmt).all())

    def list_by_scorer(
        self,
        session: Session,
        scorer_name: str,
        dataset_name: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[EvalResult]:
        """Return results for a scorer, optionally filtered by dataset."""
        conditions = [EvalResult.scorer_name == scorer_name]
        if dataset_name is not None:
            conditions.append(EvalResult.dataset_name == dataset_name)
        stmt = (
            select(EvalResult)
            .where(*conditions)
            .order_by(EvalResult.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(stmt).all())

    def list_by_dataset(
        self,
        session: Session,
        dataset_name: str,
        limit: int = 200,
        offset: int = 0,
    ) -> list[EvalResult]:
        """Return results for a dataset, most recent first."""
        stmt = (
            select(EvalResult)
            .where(EvalResult.dataset_name == dataset_name)
            .order_by(EvalResult.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(stmt).all())
