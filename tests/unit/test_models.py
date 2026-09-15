"""Unit tests for SQLAlchemy models and database schema definitions."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.db.models import (
    AuditLog,
    Base,
    EvalResult,
    HITLRequest,
    HITLStatus,
    Message,
    MessageRole,
    Run,
    RunStatus,
    Task,
    TaskStatus,
    ToolCall,
    ToolCallStatus,
    User,
)


@pytest.fixture
def db_engine():
    """Create an in-memory SQLite engine for model testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """Provide a transactional database session for testing."""
    with Session(db_engine) as session:
        yield session


def test_metadata_contains_all_expected_tables():
    """Verify that all architecture-mandated tables are present in Base.metadata."""
    expected_tables = {
        "users",
        "tasks",
        "runs",
        "messages",
        "tool_calls",
        "hitl_requests",
        "audit_logs",
        "eval_results",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(actual_tables)


def test_user_creation_and_repr(db_session: Session):
    """Verify User model creation, defaults, and repr representation."""
    user = User(
        email="operator@example.com",
        name="Lead Operator",
    )
    db_session.add(user)
    db_session.commit()

    assert isinstance(user.id, uuid.UUID)
    assert user.email == "operator@example.com"
    assert user.name == "Lead Operator"
    assert user.is_active is True
    assert isinstance(user.created_at, datetime)
    assert isinstance(user.updated_at, datetime)
    assert f"<User(id={user.id}, email='operator@example.com')>" == repr(user)


def test_user_email_uniqueness_constraint(db_session: Session):
    """Verify that User email uniqueness constraint is enforced."""
    user1 = User(email="unique@example.com")
    db_session.add(user1)
    db_session.commit()

    user2 = User(email="unique@example.com")
    db_session.add(user2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_task_creation_with_defaults(db_session: Session):
    """Verify Task creation with default status, metadata, and JSON input."""
    task = Task(
        title="Research Query Task",
        input_data={"query": "Analyze market trends"},
    )
    db_session.add(task)
    db_session.commit()

    assert isinstance(task.id, uuid.UUID)
    assert task.status == TaskStatus.QUEUED
    assert task.input_data == {"query": "Analyze market trends"}
    assert task.task_metadata == {}
    assert task.result is None
    assert task.error_message is None
    expected_repr = (
        f"<Task(id={task.id}, status='TaskStatus.QUEUED', title='Research Query Task')>"
    )
    assert repr(task) == expected_repr


def test_task_user_relationship(db_session: Session):
    """Verify relationship between User and Task."""
    user = User(email="researcher@example.com")
    task = Task(
        title="Assigned Task",
        input_data={"prompt": "Summarize paper"},
        user=user,
    )
    db_session.add(user)
    db_session.add(task)
    db_session.commit()

    retrieved_task = db_session.get(Task, task.id)
    assert retrieved_task is not None
    assert retrieved_task.user is not None
    assert retrieved_task.user.email == "researcher@example.com"
    assert len(user.tasks) == 1
    assert user.tasks[0].id == task.id


def test_run_creation_and_task_relationship(db_session: Session):
    """Verify Run creation, execution fields, and relationship to Task."""
    task = Task(
        title="Execution Task",
        input_data={"action": "run_analysis"},
    )
    db_session.add(task)
    db_session.commit()

    run = Run(
        task_id=task.id,
        status=RunStatus.RUNNING,
        celery_task_id="celery-uuid-12345",
        checkpoint_id="chk-node-router-1",
        current_node="router_agent",
        retry_count=1,
        state_snapshot={"active_agent": "router"},
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(run)
    db_session.commit()

    assert isinstance(run.id, uuid.UUID)
    assert run.task_id == task.id
    assert run.status == RunStatus.RUNNING
    assert run.celery_task_id == "celery-uuid-12345"
    assert run.current_node == "router_agent"
    assert run.retry_count == 1
    assert run.state_snapshot == {"active_agent": "router"}
    expected_repr = f"<Run(id={run.id}, task_id={task.id}, status='RunStatus.RUNNING')>"
    assert repr(run) == expected_repr

    # Check relationship navigation
    assert len(task.runs) == 1
    assert task.runs[0].id == run.id
    assert run.task.id == task.id


def test_message_episodic_memory_creation(db_session: Session):
    """Verify Message model representing episodic memory."""
    task = Task(
        title="Chat Task",
        input_data={"prompt": "Hello"},
    )
    run = Run(task=task)
    db_session.add_all([task, run])
    db_session.commit()

    msg1 = Message(
        task_id=task.id,
        run_id=run.id,
        role=MessageRole.USER,
        content="Please find latest research",
    )
    msg2 = Message(
        task_id=task.id,
        run_id=run.id,
        role=MessageRole.ASSISTANT,
        agent_role="Researcher",
        content="Searching internal knowledge base...",
        tokens=42,
        msg_metadata={"source": "kb_retrieval"},
    )
    db_session.add_all([msg1, msg2])
    db_session.commit()

    assert msg1.role == MessageRole.USER
    assert msg2.role == MessageRole.ASSISTANT
    assert msg2.agent_role == "Researcher"
    assert msg2.tokens == 42
    assert msg2.msg_metadata == {"source": "kb_retrieval"}
    expected_msg1_repr = (
        f"<Message(id={msg1.id}, task_id={task.id}, role='MessageRole.USER')>"
    )
    assert repr(msg1) == expected_msg1_repr

    # Check task messages navigation
    assert len(task.messages) == 2
    assert len(run.messages) == 2


def test_tool_call_logging(db_session: Session):
    """Verify ToolCall model for logging tool invocations."""
    task = Task(
        title="Tool Call Task",
        input_data={"action": "search"},
    )
    run = Run(task=task)
    db_session.add_all([task, run])
    db_session.commit()

    tool_call = ToolCall(
        task_id=task.id,
        run_id=run.id,
        agent_role="Executor",
        tool_name="web_search",
        input_arguments={"query": "LangGraph multi-agent"},
        output_result={"status": "success", "results": ["link1", "link2"]},
        status=ToolCallStatus.SUCCESS,
        duration_ms=254.5,
    )
    db_session.add(tool_call)
    db_session.commit()

    assert isinstance(tool_call.id, uuid.UUID)
    assert tool_call.tool_name == "web_search"
    assert tool_call.status == ToolCallStatus.SUCCESS
    assert tool_call.duration_ms == 254.5
    assert tool_call.input_arguments["query"] == "LangGraph multi-agent"
    expected_repr = (
        f"<ToolCall(id={tool_call.id}, tool='web_search', "
        "status='ToolCallStatus.SUCCESS')>"
    )
    assert repr(tool_call) == expected_repr
    assert len(task.tool_calls) == 1
    assert len(run.tool_calls) == 1


def test_hitl_request_lifecycle(db_session: Session):
    """Verify HITLRequest creation, escalation status, and human decision."""
    operator = User(email="human_reviewer@example.com")
    task = Task(
        title="Escalated Task",
        input_data={"sensitive_operation": True},
        status=TaskStatus.PENDING_HUMAN,
    )
    run = Run(task=task, status=RunStatus.ESCALATED)
    db_session.add_all([operator, task, run])
    db_session.commit()

    hitl = HITLRequest(
        task_id=task.id,
        run_id=run.id,
        status=HITLStatus.PENDING,
        reason="Critic flagged low confidence score (0.42)",
        context_data={"confidence": 0.42, "proposed_action": "delete_resource"},
    )
    db_session.add(hitl)
    db_session.commit()

    assert hitl.status == HITLStatus.PENDING
    assert hitl.decision is None
    expected_hitl_repr = (
        f"<HITLRequest(id={hitl.id}, task_id={task.id}, status='HITLStatus.PENDING')>"
    )
    assert repr(hitl) == expected_hitl_repr

    # Human decides to approve
    hitl.decision = HITLStatus.APPROVED
    hitl.status = HITLStatus.APPROVED
    hitl.decision_payload = {"notes": "Approved by human operator"}
    hitl.decided_by_id = operator.id
    hitl.decided_at = datetime.now(timezone.utc)
    task.status = TaskStatus.RESUMING
    db_session.commit()

    refreshed_hitl = db_session.get(HITLRequest, hitl.id)
    assert refreshed_hitl is not None
    assert refreshed_hitl.status == HITLStatus.APPROVED
    assert refreshed_hitl.decision == HITLStatus.APPROVED
    assert refreshed_hitl.decided_by_user is not None
    assert refreshed_hitl.decided_by_user.email == "human_reviewer@example.com"
    assert len(operator.hitl_decisions) == 1


def test_audit_log_entry(db_session: Session):
    """Verify AuditLog immutable logging."""
    user = User(email="actor@example.com")
    task = Task(title="Audit Task", input_data={})
    db_session.add_all([user, task])
    db_session.commit()

    log_entry = AuditLog(
        event_type="TASK_CREATED",
        entity_type="task",
        entity_id=str(task.id),
        task_id=task.id,
        user_id=user.id,
        details={"ip": "127.0.0.1", "action": "submit"},
    )
    db_session.add(log_entry)
    db_session.commit()

    assert isinstance(log_entry.id, uuid.UUID)
    assert log_entry.event_type == "TASK_CREATED"
    assert log_entry.details == {"ip": "127.0.0.1", "action": "submit"}
    expected_repr = (
        f"<AuditLog(id={log_entry.id}, event='TASK_CREATED', entity='task')>"
    )
    assert repr(log_entry) == expected_repr
    assert len(task.audit_logs) == 1
    assert len(user.audit_logs) == 1


def test_eval_result_entry(db_session: Session):
    """Verify EvalResult recording."""
    task = Task(title="Evaluated Task", input_data={"prompt": "Translate"})
    db_session.add(task)
    db_session.commit()

    eval_result = EvalResult(
        eval_run_id="eval-batch-2026-09-16",
        dataset_name="golden_tasks_v1",
        task_id=task.id,
        scorer_name="correctness",
        score=0.95,
        metrics={"precision": 0.96, "recall": 0.94},
        details={"reasoning": "Output matches gold standard"},
    )
    db_session.add(eval_result)
    db_session.commit()

    assert isinstance(eval_result.id, uuid.UUID)
    assert eval_result.scorer_name == "correctness"
    assert eval_result.score == 0.95
    expected_repr = (
        f"<EvalResult(id={eval_result.id}, scorer='correctness', score=0.95)>"
    )
    assert repr(eval_result) == expected_repr
    assert len(task.eval_results) == 1


def test_task_cascade_deletion(db_session: Session):
    """Verify deleting a Task cascades to associated child records."""
    task = Task(title="Cascade Task", input_data={})
    run = Run(task=task)
    msg = Message(task=task, run=run, role=MessageRole.USER, content="Hello")
    tool = ToolCall(task=task, run=run, tool_name="search", input_arguments={})
    hitl = HITLRequest(task=task, run=run, reason="Test")
    db_session.add_all([task, run, msg, tool, hitl])
    db_session.commit()

    task_id = task.id
    run_id = run.id
    msg_id = msg.id
    tool_id = tool.id
    hitl_id = hitl.id

    # Delete task
    db_session.delete(task)
    db_session.commit()

    assert db_session.get(Task, task_id) is None
    assert db_session.get(Run, run_id) is None
    assert db_session.get(Message, msg_id) is None
    assert db_session.get(ToolCall, tool_id) is None
    assert db_session.get(HITLRequest, hitl_id) is None


def test_user_deletion_sets_null_on_task(db_session: Session):
    """Verify deleting a User preserves Tasks and sets user_id to NULL."""
    user = User(email="to_delete@example.com")
    task = Task(title="Preserved Task", input_data={}, user=user)
    db_session.add_all([user, task])
    db_session.commit()

    task_id = task.id
    db_session.delete(user)
    db_session.commit()

    refreshed_task = db_session.get(Task, task_id)
    assert refreshed_task is not None
    assert refreshed_task.user_id is None
    assert refreshed_task.user is None


def test_session_helpers():
    """Verify session and engine helper functions in src/db/session.py."""
    from src.db.session import get_db_session, get_engine, get_session_factory

    engine = get_engine("sqlite:///:memory:")
    assert engine is not None
    factory = get_session_factory(engine)
    assert factory is not None

    session_gen = get_db_session(engine)
    session = next(session_gen)
    assert isinstance(session, Session)
    # verify cleanup on generator completion
    with pytest.raises(StopIteration):
        next(session_gen)
    engine.dispose()


def test_task_runs_ordering(db_session: Session):
    """Verify runs and messages attached to a task are ordered by creation timestamp."""
    task = Task(title="Sequential Task", input_data={})
    db_session.add(task)
    db_session.commit()

    run1 = Run(task=task, current_node="node_1")
    run2 = Run(task=task, current_node="node_2")
    db_session.add_all([run1, run2])
    db_session.commit()

    refreshed_task = db_session.get(Task, task.id)
    assert refreshed_task is not None
    assert len(refreshed_task.runs) == 2
    assert refreshed_task.runs[0].id == run1.id
    assert refreshed_task.runs[1].id == run2.id
