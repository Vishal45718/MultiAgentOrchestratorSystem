"""Repository layer — data-access classes for all domain models.

Repositories take an injected ``sqlalchemy.orm.Session`` and never call
``session.commit()``.  Transaction control belongs to the caller so that
multi-repository operations can be wrapped in a single atomic transaction.
"""

from src.db.repositories.audit_log import AuditLogRepository
from src.db.repositories.base import NotFoundError
from src.db.repositories.eval_result import EvalResultRepository
from src.db.repositories.hitl_request import HITLRequestRepository
from src.db.repositories.message import MessageRepository
from src.db.repositories.run import RunRepository
from src.db.repositories.task import TaskRepository
from src.db.repositories.tool_call import ToolCallRepository
from src.db.repositories.user import UserRepository

__all__ = [
    "NotFoundError",
    "UserRepository",
    "TaskRepository",
    "RunRepository",
    "MessageRepository",
    "ToolCallRepository",
    "HITLRequestRepository",
    "AuditLogRepository",
    "EvalResultRepository",
]
