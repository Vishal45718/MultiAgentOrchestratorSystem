"""SQLAlchemy database models for the Multi-Agent Orchestration System."""

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)

# Dialect-agnostic JSON: PostgreSQL JSONB, fallback to standard JSON on SQLite
JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base class for all database models."""

    pass


class TaskStatus(str, enum.Enum):
    """Lifecycle status of an orchestration task."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PENDING_HUMAN = "PENDING_HUMAN"
    RESUMING = "RESUMING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RunStatus(str, enum.Enum):
    """Status of an individual graph/agent execution run."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"
    CANCELLED = "CANCELLED"


class MessageRole(str, enum.Enum):
    """Role of an episodic message sender."""

    SYSTEM = "SYSTEM"
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    TOOL = "TOOL"


class ToolCallStatus(str, enum.Enum):
    """Outcome status of a tool invocation."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    TIMEOUT = "TIMEOUT"
    RETRY = "RETRY"


class HITLStatus(str, enum.Enum):
    """Status of a human-in-the-loop escalation request."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EDITED = "EDITED"


class TimestampMixin:
    """Common timestamp fields for models."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        onupdate=utc_now,
        nullable=False,
    )


class User(Base, TimestampMixin):
    """User entity representing an account or system actor."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    tasks: Mapped[list["Task"]] = relationship(back_populates="user")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")
    hitl_decisions: Mapped[list["HITLRequest"]] = relationship(
        back_populates="decided_by_user",
        foreign_keys="[HITLRequest.decided_by_id]",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}')>"


class Task(Base, TimestampMixin):
    """Durable task submitted to the multi-agent system."""

    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    input_data: Mapped[dict[str, Any]] = mapped_column(
        JSON_TYPE, nullable=False, default=dict
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False),
        default=TaskStatus.QUEUED,
        nullable=False,
        index=True,
    )
    current_step: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    result: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON_TYPE, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    task_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON_TYPE, nullable=False, default=dict
    )

    # Relationships
    user: Mapped[Optional[User]] = relationship(back_populates="tasks")
    runs: Mapped[list["Run"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="Run.created_at",
    )
    messages: Mapped[list["Message"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    tool_calls: Mapped[list["ToolCall"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="ToolCall.created_at",
    )
    hitl_requests: Mapped[list["HITLRequest"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="HITLRequest.created_at",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="task")
    eval_results: Mapped[list["EvalResult"]] = relationship(back_populates="task")

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, status='{self.status}', title='{self.title}')>"


class Run(Base, TimestampMixin):
    """Execution run of a task through the agent graph / Celery worker."""

    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, native_enum=False),
        default=RunStatus.PENDING,
        nullable=False,
        index=True,
    )
    celery_task_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    checkpoint_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    current_node: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    state_snapshot: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON_TYPE, nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    task: Mapped[Task] = relationship(back_populates="runs")
    messages: Mapped[list["Message"]] = relationship(back_populates="run")
    tool_calls: Mapped[list["ToolCall"]] = relationship(back_populates="run")
    hitl_requests: Mapped[list["HITLRequest"]] = relationship(back_populates="run")

    def __repr__(self) -> str:
        return f"<Run(id={self.id}, task_id={self.task_id}, status='{self.status}')>"


class Message(Base):
    """Episodic memory message generated during task execution."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, native_enum=False), nullable=False
    )
    agent_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    msg_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON_TYPE, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    task: Mapped[Task] = relationship(back_populates="messages")
    run: Mapped[Optional[Run]] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, task_id={self.task_id}, role='{self.role}')>"


class ToolCall(Base):
    """Record of a tool invocation executed during agent processing."""

    __tablename__ = "tool_calls"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    agent_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    input_arguments: Mapped[dict[str, Any]] = mapped_column(
        JSON_TYPE, nullable=False, default=dict
    )
    output_result: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON_TYPE, nullable=True
    )
    status: Mapped[ToolCallStatus] = mapped_column(
        Enum(ToolCallStatus, native_enum=False),
        default=ToolCallStatus.SUCCESS,
        nullable=False,
        index=True,
    )
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    task: Mapped[Task] = relationship(back_populates="tool_calls")
    run: Mapped[Optional[Run]] = relationship(back_populates="tool_calls")

    def __repr__(self) -> str:
        return (
            f"<ToolCall(id={self.id}, tool='{self.tool_name}', status='{self.status}')>"
        )


class HITLRequest(Base, TimestampMixin):
    """Human-in-the-loop escalation request."""

    __tablename__ = "hitl_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[HITLStatus] = mapped_column(
        Enum(HITLStatus, native_enum=False),
        default=HITLStatus.PENDING,
        nullable=False,
        index=True,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    context_data: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON_TYPE, nullable=True
    )
    decision: Mapped[Optional[HITLStatus]] = mapped_column(
        Enum(HITLStatus, native_enum=False), nullable=True
    )
    decision_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON_TYPE, nullable=True
    )
    decided_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    decided_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    task: Mapped[Task] = relationship(back_populates="hitl_requests")
    run: Mapped[Optional[Run]] = relationship(back_populates="hitl_requests")
    decided_by_user: Mapped[Optional[User]] = relationship(
        back_populates="hitl_decisions",
        foreign_keys=[decided_by_id],
    )

    def __repr__(self) -> str:
        return (
            f"<HITLRequest(id={self.id}, task_id={self.task_id}, "
            f"status='{self.status}')>"
        )


class AuditLog(Base):
    """System-wide immutable audit trail for security and governance."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON_TYPE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    task: Mapped[Optional[Task]] = relationship(back_populates="audit_logs")
    user: Mapped[Optional[User]] = relationship(back_populates="audit_logs")

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, event='{self.event_type}', "
            f"entity='{self.entity_type}')>"
        )


class EvalResult(Base):
    """Offline or online evaluation metric score stored in Postgres."""

    __tablename__ = "eval_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    eval_run_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    dataset_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    scorer_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    metrics: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON_TYPE, nullable=True)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON_TYPE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    task: Mapped[Optional[Task]] = relationship(back_populates="eval_results")

    def __repr__(self) -> str:
        return (
            f"<EvalResult(id={self.id}, scorer='{self.scorer_name}', "
            f"score={self.score})>"
        )


__all__ = [
    "Base",
    "TimestampMixin",
    "TaskStatus",
    "RunStatus",
    "MessageRole",
    "ToolCallStatus",
    "HITLStatus",
    "User",
    "Task",
    "Run",
    "Message",
    "ToolCall",
    "HITLRequest",
    "AuditLog",
    "EvalResult",
]
