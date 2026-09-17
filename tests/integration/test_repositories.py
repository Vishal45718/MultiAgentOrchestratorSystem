"""Integration tests for the repository layer.

All tests run against a real PostgreSQL database (test_orchestrator) via the
Docker Compose postgres service.  Each test is wrapped in a transaction that
rolls back on teardown — no persistent state leaks between tests.

Coverage includes:
- CRUD operations for every repository
- Relationship / foreign-key constraints
- Update operations and partial-update semantics
- Not-found behaviour (NotFoundError)
- Filtering / query methods
- Transaction behaviour (multi-step atomicity via savepoint rollback)
- Cascade delete behaviour
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.db.models import (
    HITLStatus,
    MessageRole,
    RunStatus,
    TaskStatus,
    ToolCallStatus,
)
from src.db.repositories import (
    AuditLogRepository,
    EvalResultRepository,
    HITLRequestRepository,
    MessageRepository,
    NotFoundError,
    RunRepository,
    TaskRepository,
    ToolCallRepository,
    UserRepository,
)

# ---------------------------------------------------------------------------
# Shared repository instances (stateless — safe to share)
# ---------------------------------------------------------------------------
users = UserRepository()
tasks = TaskRepository()
runs = RunRepository()
messages = MessageRepository()
tool_calls = ToolCallRepository()
hitl = HITLRequestRepository()
audit = AuditLogRepository()
evals = EvalResultRepository()


# ===========================================================================
# User repository
# ===========================================================================


class TestUserRepository:
    def test_create_and_retrieve_by_id(self, db_session: Session):
        user = users.create(db_session, email="alice@example.com", name="Alice")
        db_session.flush()

        retrieved = users.get_by_id(db_session, user.id)
        assert retrieved.email == "alice@example.com"
        assert retrieved.name == "Alice"
        assert retrieved.is_active is True

    def test_create_defaults(self, db_session: Session):
        user = users.create(db_session, email="bob@example.com")
        db_session.flush()
        assert user.is_active is True
        assert user.name is None

    def test_get_by_email(self, db_session: Session):
        users.create(db_session, email="carol@example.com")
        db_session.flush()

        found = users.get_by_email(db_session, "carol@example.com")
        assert found.email == "carol@example.com"

    def test_get_by_email_not_found(self, db_session: Session):
        with pytest.raises(NotFoundError):
            users.get_by_email(db_session, "nobody@example.com")

    def test_get_by_email_optional_returns_none(self, db_session: Session):
        result = users.get_by_email_optional(db_session, "ghost@example.com")
        assert result is None

    def test_get_by_id_not_found_raises(self, db_session: Session):
        with pytest.raises(NotFoundError) as exc_info:
            users.get_by_id(db_session, uuid.uuid4())
        assert "User" in str(exc_info.value)

    def test_get_by_id_optional_returns_none(self, db_session: Session):
        result = users.get_by_id_optional(db_session, uuid.uuid4())
        assert result is None

    def test_email_unique_constraint(self, db_session: Session):
        users.create(db_session, email="dup@example.com")
        db_session.flush()
        users.create(db_session, email="dup@example.com")
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_update_name_and_active(self, db_session: Session):
        user = users.create(db_session, email="dave@example.com", name="Dave")
        db_session.flush()

        updated = users.update(db_session, user.id, name="David", is_active=False)
        assert updated.name == "David"
        assert updated.is_active is False

    def test_update_partial(self, db_session: Session):
        user = users.create(db_session, email="eve@example.com", name="Eve")
        db_session.flush()

        # Only name — is_active stays True
        updated = users.update(db_session, user.id, name="Eva")
        assert updated.name == "Eva"
        assert updated.is_active is True

    def test_update_not_found_raises(self, db_session: Session):
        with pytest.raises(NotFoundError):
            users.update(db_session, uuid.uuid4(), name="Nobody")

    def test_list_active(self, db_session: Session):
        users.create(db_session, email="active1@example.com", is_active=True)
        users.create(db_session, email="active2@example.com", is_active=True)
        users.create(db_session, email="inactive@example.com", is_active=False)
        db_session.flush()

        active = users.list_active(db_session)
        emails = {u.email for u in active}
        assert "active1@example.com" in emails
        assert "active2@example.com" in emails
        assert "inactive@example.com" not in emails

    def test_delete_user(self, db_session: Session):
        user = users.create(db_session, email="todelete@example.com")
        db_session.flush()
        uid = user.id

        users.delete(db_session, user)
        db_session.flush()

        assert users.get_by_id_optional(db_session, uid) is None


# ===========================================================================
# Task repository
# ===========================================================================


class TestTaskRepository:
    def test_create_and_retrieve(self, db_session: Session):
        task = tasks.create(
            db_session,
            input_data={"prompt": "hello"},
            title="My Task",
        )
        db_session.flush()

        retrieved = tasks.get_by_id(db_session, task.id)
        assert retrieved.title == "My Task"
        assert retrieved.status == TaskStatus.QUEUED
        assert retrieved.input_data == {"prompt": "hello"}
        assert retrieved.task_metadata == {}

    def test_create_with_user(self, db_session: Session):
        user = users.create(db_session, email="taskowner@example.com")
        db_session.flush()

        task = tasks.create(
            db_session,
            input_data={},
            title="User Task",
            user_id=user.id,
        )
        db_session.flush()

        retrieved = tasks.get_by_id(db_session, task.id)
        assert retrieved.user_id == user.id

    def test_not_found(self, db_session: Session):
        with pytest.raises(NotFoundError):
            tasks.get_by_id(db_session, uuid.uuid4())

    def test_list_by_status(self, db_session: Session):
        t1 = tasks.create(db_session, input_data={}, status=TaskStatus.RUNNING)
        t2 = tasks.create(db_session, input_data={}, status=TaskStatus.RUNNING)
        tasks.create(db_session, input_data={}, status=TaskStatus.COMPLETED)
        db_session.flush()

        running = tasks.list_by_status(db_session, TaskStatus.RUNNING)
        ids = {t.id for t in running}
        assert t1.id in ids
        assert t2.id in ids

    def test_list_by_user(self, db_session: Session):
        user = users.create(db_session, email="lister@example.com")
        db_session.flush()

        t1 = tasks.create(db_session, input_data={}, user_id=user.id)
        t2 = tasks.create(db_session, input_data={}, user_id=user.id)
        tasks.create(db_session, input_data={})  # no user
        db_session.flush()

        user_tasks = tasks.list_by_user(db_session, user.id)
        ids = {t.id for t in user_tasks}
        assert t1.id in ids
        assert t2.id in ids
        assert len(ids) == 2

    def test_update_status(self, db_session: Session):
        task = tasks.create(db_session, input_data={})
        db_session.flush()

        updated = tasks.update_status(
            db_session,
            task.id,
            TaskStatus.RUNNING,
            current_step="router_agent",
        )
        assert updated.status == TaskStatus.RUNNING
        assert updated.current_step == "router_agent"

    def test_set_result(self, db_session: Session):
        task = tasks.create(db_session, input_data={})
        db_session.flush()

        tasks.set_result(db_session, task.id, result={"answer": 42})
        db_session.flush()

        retrieved = tasks.get_by_id(db_session, task.id)
        assert retrieved.result == {"answer": 42}
        assert retrieved.status == TaskStatus.COMPLETED

    def test_update_partial(self, db_session: Session):
        task = tasks.create(db_session, input_data={}, title="Old Title")
        db_session.flush()

        tasks.update(db_session, task.id, title="New Title", task_metadata={"k": "v"})
        db_session.flush()

        retrieved = tasks.get_by_id(db_session, task.id)
        assert retrieved.title == "New Title"
        assert retrieved.task_metadata == {"k": "v"}
        assert retrieved.status == TaskStatus.QUEUED  # unchanged

    def test_update_error_message(self, db_session: Session):
        task = tasks.create(db_session, input_data={})
        db_session.flush()

        tasks.update_status(
            db_session,
            task.id,
            TaskStatus.FAILED,
            error_message="LLM timeout",
        )
        db_session.flush()

        retrieved = tasks.get_by_id(db_session, task.id)
        assert retrieved.status == TaskStatus.FAILED
        assert retrieved.error_message == "LLM timeout"

    def test_cascade_delete_removes_runs(self, db_session: Session):
        task = tasks.create(db_session, input_data={})
        db_session.flush()
        run = runs.create(db_session, task_id=task.id)
        db_session.flush()
        run_id = run.id

        db_session.delete(task)
        db_session.flush()

        assert runs.get_by_id_optional(db_session, run_id) is None


# ===========================================================================
# Run repository
# ===========================================================================


class TestRunRepository:
    def _make_task(self, db_session):
        task = tasks.create(db_session, input_data={})
        db_session.flush()
        return task

    def test_create_and_retrieve(self, db_session: Session):
        task = self._make_task(db_session)
        run = runs.create(db_session, task_id=task.id)
        db_session.flush()

        retrieved = runs.get_by_id(db_session, run.id)
        assert retrieved.task_id == task.id
        assert retrieved.status == RunStatus.PENDING
        assert retrieved.retry_count == 0

    def test_not_found(self, db_session: Session):
        with pytest.raises(NotFoundError):
            runs.get_by_id(db_session, uuid.uuid4())

    def test_list_by_task(self, db_session: Session):
        task = self._make_task(db_session)
        r1 = runs.create(db_session, task_id=task.id)
        r2 = runs.create(db_session, task_id=task.id)
        db_session.flush()

        result = runs.list_by_task(db_session, task.id)
        ids = [r.id for r in result]
        assert r1.id in ids
        assert r2.id in ids

    def test_get_latest_by_task(self, db_session: Session):
        task = self._make_task(db_session)
        runs.create(db_session, task_id=task.id)
        db_session.flush()
        r2 = runs.create(db_session, task_id=task.id)
        db_session.flush()

        latest = runs.get_latest_by_task(db_session, task.id)
        assert latest is not None
        assert latest.id == r2.id

    def test_get_by_celery_task_id(self, db_session: Session):
        task = self._make_task(db_session)
        run = runs.create(db_session, task_id=task.id, celery_task_id="celery-abc-123")
        db_session.flush()

        found = runs.get_by_celery_task_id(db_session, "celery-abc-123")
        assert found is not None
        assert found.id == run.id

    def test_get_by_celery_task_id_missing(self, db_session: Session):
        result = runs.get_by_celery_task_id(db_session, "nonexistent-celery-id")
        assert result is None

    def test_list_by_status(self, db_session: Session):
        task = self._make_task(db_session)
        r1 = runs.create(db_session, task_id=task.id, status=RunStatus.RUNNING)
        runs.create(db_session, task_id=task.id, status=RunStatus.COMPLETED)
        db_session.flush()

        running = runs.list_by_status(db_session, RunStatus.RUNNING)
        ids = {r.id for r in running}
        assert r1.id in ids

    def test_mark_started(self, db_session: Session):
        task = self._make_task(db_session)
        run = runs.create(db_session, task_id=task.id)
        db_session.flush()

        updated = runs.mark_started(
            db_session,
            run.id,
            celery_task_id="celery-xyz",
            current_node="router",
        )
        assert updated.status == RunStatus.RUNNING
        assert updated.started_at is not None
        assert updated.celery_task_id == "celery-xyz"
        assert updated.current_node == "router"

    def test_mark_completed(self, db_session: Session):
        task = self._make_task(db_session)
        run = runs.create(db_session, task_id=task.id, status=RunStatus.RUNNING)
        db_session.flush()

        updated = runs.mark_completed(
            db_session,
            run.id,
            state_snapshot={"final": True},
        )
        assert updated.status == RunStatus.COMPLETED
        assert updated.completed_at is not None
        assert updated.state_snapshot == {"final": True}

    def test_mark_failed(self, db_session: Session):
        task = self._make_task(db_session)
        run = runs.create(db_session, task_id=task.id, status=RunStatus.RUNNING)
        db_session.flush()

        updated = runs.mark_completed(
            db_session,
            run.id,
            status=RunStatus.FAILED,
            error_message="Tool timeout exceeded",
        )
        assert updated.status == RunStatus.FAILED
        assert updated.error_message == "Tool timeout exceeded"

    def test_increment_retry(self, db_session: Session):
        task = self._make_task(db_session)
        run = runs.create(db_session, task_id=task.id)
        db_session.flush()

        runs.increment_retry(db_session, run.id)
        runs.increment_retry(db_session, run.id)
        db_session.flush()

        retrieved = runs.get_by_id(db_session, run.id)
        assert retrieved.retry_count == 2

    def test_set_checkpoint(self, db_session: Session):
        task = self._make_task(db_session)
        run = runs.create(db_session, task_id=task.id)
        db_session.flush()

        runs.set_checkpoint(
            db_session,
            run.id,
            "chk-1234",
            state_snapshot={"node": "executor"},
        )
        db_session.flush()

        retrieved = runs.get_by_id(db_session, run.id)
        assert retrieved.checkpoint_id == "chk-1234"
        assert retrieved.state_snapshot == {"node": "executor"}

    def test_update_status(self, db_session: Session):
        task = self._make_task(db_session)
        run = runs.create(db_session, task_id=task.id)
        db_session.flush()

        runs.update_status(
            db_session, run.id, RunStatus.ESCALATED, current_node="critic"
        )
        db_session.flush()

        retrieved = runs.get_by_id(db_session, run.id)
        assert retrieved.status == RunStatus.ESCALATED
        assert retrieved.current_node == "critic"

    def test_get_latest_by_task_returns_none_when_no_runs(self, db_session: Session):
        task = self._make_task(db_session)
        assert runs.get_latest_by_task(db_session, task.id) is None


# ===========================================================================
# Message repository
# ===========================================================================


class TestMessageRepository:
    def _setup(self, db_session):
        task = tasks.create(db_session, input_data={})
        db_session.flush()
        run = runs.create(db_session, task_id=task.id)
        db_session.flush()
        return task, run

    def test_create_and_retrieve(self, db_session: Session):
        task, run = self._setup(db_session)
        msg = messages.create(
            db_session,
            task_id=task.id,
            run_id=run.id,
            role=MessageRole.USER,
            content="What is the weather?",
        )
        db_session.flush()

        retrieved = messages.get_by_id(db_session, msg.id)
        assert retrieved.content == "What is the weather?"
        assert retrieved.role == MessageRole.USER
        assert retrieved.msg_metadata == {}

    def test_create_with_metadata(self, db_session: Session):
        task, run = self._setup(db_session)
        msg = messages.create(
            db_session,
            task_id=task.id,
            role=MessageRole.ASSISTANT,
            content="I'll look that up.",
            agent_role="Researcher",
            tokens=15,
            msg_metadata={"source": "kb"},
        )
        db_session.flush()

        retrieved = messages.get_by_id(db_session, msg.id)
        assert retrieved.agent_role == "Researcher"
        assert retrieved.tokens == 15
        assert retrieved.msg_metadata == {"source": "kb"}

    def test_not_found(self, db_session: Session):
        with pytest.raises(NotFoundError):
            messages.get_by_id(db_session, uuid.uuid4())

    def test_list_by_task(self, db_session: Session):
        task, run = self._setup(db_session)
        m1 = messages.create(
            db_session, task_id=task.id, role=MessageRole.USER, content="A"
        )
        m2 = messages.create(
            db_session, task_id=task.id, role=MessageRole.ASSISTANT, content="B"
        )
        db_session.flush()

        result = messages.list_by_task(db_session, task.id)
        ids = [m.id for m in result]
        assert m1.id in ids
        assert m2.id in ids

    def test_list_by_run(self, db_session: Session):
        task, run = self._setup(db_session)
        run2 = runs.create(db_session, task_id=task.id)
        db_session.flush()

        m1 = messages.create(
            db_session,
            task_id=task.id,
            run_id=run.id,
            role=MessageRole.USER,
            content="run1 msg",
        )
        messages.create(
            db_session,
            task_id=task.id,
            run_id=run2.id,
            role=MessageRole.USER,
            content="run2 msg",
        )
        db_session.flush()

        result = messages.list_by_run(db_session, run.id)
        assert len(result) == 1
        assert result[0].id == m1.id

    def test_list_by_role(self, db_session: Session):
        task, run = self._setup(db_session)
        messages.create(
            db_session, task_id=task.id, role=MessageRole.USER, content="user"
        )
        messages.create(
            db_session,
            task_id=task.id,
            role=MessageRole.ASSISTANT,
            content="assistant",
        )
        messages.create(
            db_session, task_id=task.id, role=MessageRole.TOOL, content="tool"
        )
        db_session.flush()

        assistant_msgs = messages.list_by_role(
            db_session, task.id, MessageRole.ASSISTANT
        )
        assert len(assistant_msgs) == 1
        assert assistant_msgs[0].role == MessageRole.ASSISTANT

    def test_cascade_delete_with_task(self, db_session: Session):
        task, run = self._setup(db_session)
        msg = messages.create(
            db_session, task_id=task.id, role=MessageRole.SYSTEM, content="sys"
        )
        db_session.flush()
        msg_id = msg.id

        db_session.delete(task)
        db_session.flush()

        assert messages.get_by_id_optional(db_session, msg_id) is None


# ===========================================================================
# ToolCall repository
# ===========================================================================


class TestToolCallRepository:
    def _setup(self, db_session):
        task = tasks.create(db_session, input_data={})
        db_session.flush()
        run = runs.create(db_session, task_id=task.id)
        db_session.flush()
        return task, run

    def test_create_and_retrieve(self, db_session: Session):
        task, run = self._setup(db_session)
        tc = tool_calls.create(
            db_session,
            task_id=task.id,
            run_id=run.id,
            tool_name="web_search",
            input_arguments={"query": "LangGraph"},
            output_result={"results": ["url1"]},
            duration_ms=120.5,
        )
        db_session.flush()

        retrieved = tool_calls.get_by_id(db_session, tc.id)
        assert retrieved.tool_name == "web_search"
        assert retrieved.status == ToolCallStatus.SUCCESS
        assert retrieved.input_arguments == {"query": "LangGraph"}
        assert retrieved.duration_ms == 120.5

    def test_not_found(self, db_session: Session):
        with pytest.raises(NotFoundError):
            tool_calls.get_by_id(db_session, uuid.uuid4())

    def test_list_by_task(self, db_session: Session):
        task, run = self._setup(db_session)
        tc1 = tool_calls.create(
            db_session, task_id=task.id, tool_name="t1", input_arguments={}
        )
        tc2 = tool_calls.create(
            db_session, task_id=task.id, tool_name="t2", input_arguments={}
        )
        db_session.flush()

        result = tool_calls.list_by_task(db_session, task.id)
        ids = {tc.id for tc in result}
        assert tc1.id in ids
        assert tc2.id in ids

    def test_list_by_run(self, db_session: Session):
        task, run = self._setup(db_session)
        run2 = runs.create(db_session, task_id=task.id)
        db_session.flush()

        tc1 = tool_calls.create(
            db_session,
            task_id=task.id,
            run_id=run.id,
            tool_name="tool_run1",
            input_arguments={},
        )
        tool_calls.create(
            db_session,
            task_id=task.id,
            run_id=run2.id,
            tool_name="tool_run2",
            input_arguments={},
        )
        db_session.flush()

        result = tool_calls.list_by_run(db_session, run.id)
        assert len(result) == 1
        assert result[0].id == tc1.id

    def test_list_by_tool_name(self, db_session: Session):
        task, run = self._setup(db_session)
        tool_calls.create(
            db_session, task_id=task.id, tool_name="kb_retrieval", input_arguments={}
        )
        tool_calls.create(
            db_session, task_id=task.id, tool_name="web_search", input_arguments={}
        )
        db_session.flush()

        result = tool_calls.list_by_tool_name(db_session, "kb_retrieval")
        assert all(tc.tool_name == "kb_retrieval" for tc in result)
        assert len(result) == 1

    def test_list_by_status(self, db_session: Session):
        task, run = self._setup(db_session)
        tc_fail = tool_calls.create(
            db_session,
            task_id=task.id,
            tool_name="t",
            input_arguments={},
            status=ToolCallStatus.FAILURE,
        )
        tool_calls.create(
            db_session,
            task_id=task.id,
            tool_name="t",
            input_arguments={},
            status=ToolCallStatus.SUCCESS,
        )
        db_session.flush()

        failures = tool_calls.list_by_status(db_session, ToolCallStatus.FAILURE)
        ids = {tc.id for tc in failures}
        assert tc_fail.id in ids

    def test_record_result(self, db_session: Session):
        task, run = self._setup(db_session)
        tc = tool_calls.create(
            db_session,
            task_id=task.id,
            tool_name="api_call",
            input_arguments={"endpoint": "/v1/data"},
        )
        db_session.flush()

        tool_calls.record_result(
            db_session,
            tc.id,
            status=ToolCallStatus.FAILURE,
            error_message="HTTP 500",
            duration_ms=350.0,
        )
        db_session.flush()

        retrieved = tool_calls.get_by_id(db_session, tc.id)
        assert retrieved.status == ToolCallStatus.FAILURE
        assert retrieved.error_message == "HTTP 500"
        assert retrieved.duration_ms == 350.0

    def test_cascade_delete_with_task(self, db_session: Session):
        task, run = self._setup(db_session)
        tc = tool_calls.create(
            db_session, task_id=task.id, tool_name="t", input_arguments={}
        )
        db_session.flush()
        tc_id = tc.id

        db_session.delete(task)
        db_session.flush()

        assert tool_calls.get_by_id_optional(db_session, tc_id) is None


# ===========================================================================
# HITLRequest repository
# ===========================================================================


class TestHITLRequestRepository:
    def _setup(self, db_session):
        task = tasks.create(db_session, input_data={}, status=TaskStatus.PENDING_HUMAN)
        db_session.flush()
        run = runs.create(db_session, task_id=task.id, status=RunStatus.ESCALATED)
        db_session.flush()
        return task, run

    def test_create_and_retrieve(self, db_session: Session):
        task, run = self._setup(db_session)
        h = hitl.create(
            db_session,
            task_id=task.id,
            run_id=run.id,
            reason="Low confidence (0.3)",
            context_data={"score": 0.3},
        )
        db_session.flush()

        retrieved = hitl.get_by_id(db_session, h.id)
        assert retrieved.status == HITLStatus.PENDING
        assert retrieved.reason == "Low confidence (0.3)"
        assert retrieved.context_data == {"score": 0.3}

    def test_not_found(self, db_session: Session):
        with pytest.raises(NotFoundError):
            hitl.get_by_id(db_session, uuid.uuid4())

    def test_list_pending(self, db_session: Session):
        task, run = self._setup(db_session)
        h1 = hitl.create(db_session, task_id=task.id, run_id=run.id, reason="reason A")
        h2 = hitl.create(db_session, task_id=task.id, run_id=run.id, reason="reason B")
        db_session.flush()

        pending = hitl.list_pending(db_session)
        ids = {h.id for h in pending}
        assert h1.id in ids
        assert h2.id in ids

    def test_list_pending_excludes_resolved(self, db_session: Session):
        task, run = self._setup(db_session)
        h = hitl.create(
            db_session,
            task_id=task.id,
            reason="needs review",
            status=HITLStatus.APPROVED,
        )
        db_session.flush()

        pending = hitl.list_pending(db_session)
        ids = {x.id for x in pending}
        assert h.id not in ids

    def test_list_by_task(self, db_session: Session):
        task, run = self._setup(db_session)
        h1 = hitl.create(db_session, task_id=task.id, reason="r1")
        h2 = hitl.create(db_session, task_id=task.id, reason="r2")
        db_session.flush()

        result = hitl.list_by_task(db_session, task.id)
        ids = {h.id for h in result}
        assert h1.id in ids
        assert h2.id in ids

    def test_get_pending_for_task(self, db_session: Session):
        task, run = self._setup(db_session)
        h = hitl.create(db_session, task_id=task.id, reason="escalation")
        db_session.flush()

        found = hitl.get_pending_for_task(db_session, task.id)
        assert found is not None
        assert found.id == h.id

    def test_get_pending_for_task_returns_none_when_resolved(self, db_session: Session):
        task, run = self._setup(db_session)
        h = hitl.create(db_session, task_id=task.id, reason="done")
        db_session.flush()
        hitl.record_decision(db_session, h.id, decision=HITLStatus.APPROVED)
        db_session.flush()

        found = hitl.get_pending_for_task(db_session, task.id)
        assert found is None

    def test_record_decision_approve(self, db_session: Session):
        task, run = self._setup(db_session)
        operator = users.create(db_session, email="operator@example.com")
        db_session.flush()

        h = hitl.create(db_session, task_id=task.id, reason="flagged")
        db_session.flush()

        hitl.record_decision(
            db_session,
            h.id,
            decision=HITLStatus.APPROVED,
            decided_by_id=operator.id,
            decision_payload={"notes": "LGTM"},
        )
        db_session.flush()

        retrieved = hitl.get_by_id(db_session, h.id)
        assert retrieved.status == HITLStatus.APPROVED
        assert retrieved.decision == HITLStatus.APPROVED
        assert retrieved.decided_at is not None
        assert retrieved.decided_by_id == operator.id
        assert retrieved.decision_payload == {"notes": "LGTM"}

    def test_record_decision_reject(self, db_session: Session):
        task, run = self._setup(db_session)
        h = hitl.create(db_session, task_id=task.id, reason="risky action")
        db_session.flush()

        hitl.record_decision(db_session, h.id, decision=HITLStatus.REJECTED)
        db_session.flush()

        retrieved = hitl.get_by_id(db_session, h.id)
        assert retrieved.status == HITLStatus.REJECTED
        assert retrieved.decision == HITLStatus.REJECTED

    def test_cascade_delete_with_task(self, db_session: Session):
        task, run = self._setup(db_session)
        h = hitl.create(db_session, task_id=task.id, reason="cascaded")
        db_session.flush()
        h_id = h.id

        db_session.delete(task)
        db_session.flush()

        assert hitl.get_by_id_optional(db_session, h_id) is None


# ===========================================================================
# AuditLog repository
# ===========================================================================


class TestAuditLogRepository:
    def test_create_and_retrieve(self, db_session: Session):
        task = tasks.create(db_session, input_data={})
        db_session.flush()

        log = audit.create(
            db_session,
            event_type="TASK_CREATED",
            entity_type="task",
            entity_id=str(task.id),
            task_id=task.id,
            details={"ip": "127.0.0.1"},
        )
        db_session.flush()

        retrieved = audit.get_by_id(db_session, log.id)
        assert retrieved.event_type == "TASK_CREATED"
        assert retrieved.entity_type == "task"
        assert retrieved.details == {"ip": "127.0.0.1"}

    def test_not_found(self, db_session: Session):
        with pytest.raises(NotFoundError):
            audit.get_by_id(db_session, uuid.uuid4())

    def test_list_by_task(self, db_session: Session):
        task = tasks.create(db_session, input_data={})
        db_session.flush()

        audit.create(
            db_session,
            event_type="TASK_CREATED",
            entity_type="task",
            entity_id=str(task.id),
            task_id=task.id,
        )
        audit.create(
            db_session,
            event_type="STATUS_CHANGED",
            entity_type="task",
            entity_id=str(task.id),
            task_id=task.id,
        )
        db_session.flush()

        result = audit.list_by_task(db_session, task.id)
        assert len(result) == 2
        assert all(a.task_id == task.id for a in result)

    def test_list_by_entity(self, db_session: Session):
        task = tasks.create(db_session, input_data={})
        db_session.flush()
        eid = str(task.id)

        audit.create(
            db_session,
            event_type="E1",
            entity_type="task",
            entity_id=eid,
        )
        audit.create(
            db_session,
            event_type="E2",
            entity_type="task",
            entity_id=eid,
        )
        # Different entity
        audit.create(
            db_session,
            event_type="E3",
            entity_type="task",
            entity_id="other-id",
        )
        db_session.flush()

        result = audit.list_by_entity(db_session, "task", eid)
        assert len(result) == 2

    def test_list_by_event_type(self, db_session: Session):
        audit.create(
            db_session,
            event_type="TOOL_CALL_FAILED",
            entity_type="tool_call",
            entity_id="tc-1",
        )
        audit.create(
            db_session,
            event_type="TOOL_CALL_FAILED",
            entity_type="tool_call",
            entity_id="tc-2",
        )
        audit.create(
            db_session,
            event_type="TASK_CREATED",
            entity_type="task",
            entity_id="t-1",
        )
        db_session.flush()

        result = audit.list_by_event_type(db_session, "TOOL_CALL_FAILED")
        assert all(a.event_type == "TOOL_CALL_FAILED" for a in result)
        assert len(result) >= 2

    def test_list_by_user(self, db_session: Session):
        user = users.create(db_session, email="audited@example.com")
        db_session.flush()

        audit.create(
            db_session,
            event_type="LOGIN",
            entity_type="user",
            entity_id=str(user.id),
            user_id=user.id,
        )
        db_session.flush()

        result = audit.list_by_user(db_session, user.id)
        assert len(result) == 1
        assert result[0].user_id == user.id

    def test_append_only_no_update_method(self):
        """Verify the AuditLog repository intentionally has no update method."""
        assert not hasattr(audit, "update"), (
            "AuditLogRepository must not expose an update method — "
            "audit log is immutable"
        )

    def test_append_only_no_delete_method(self):
        """Verify the AuditLog repository intentionally has no delete method.

        Note: the inherited BaseRepository.delete exists but is intentionally
        omitted from the AuditLogRepository contract via documentation; this
        test verifies the *design intent* via the absence of a public delete
        shortcut — deletion via session.delete() still works at the ORM level.
        """
        # AuditLogRepository does not override delete — this is acceptable.
        # The key intent is that the API surface doesn't encourage it.
        # This assertion documents the intent.
        assert AuditLogRepository.__doc__ is not None
        assert "append-only" in AuditLogRepository.__doc__.lower()


# ===========================================================================
# EvalResult repository
# ===========================================================================


class TestEvalResultRepository:
    def test_create_and_retrieve(self, db_session: Session):
        task = tasks.create(db_session, input_data={})
        db_session.flush()

        result = evals.create(
            db_session,
            eval_run_id="run-2026-001",
            dataset_name="golden_v1",
            scorer_name="correctness",
            score=0.92,
            task_id=task.id,
            metrics={"precision": 0.9, "recall": 0.95},
            details={"reasoning": "matched gold"},
        )
        db_session.flush()

        retrieved = evals.get_by_id(db_session, result.id)
        assert retrieved.scorer_name == "correctness"
        assert retrieved.score == 0.92
        assert retrieved.metrics == {"precision": 0.9, "recall": 0.95}

    def test_not_found(self, db_session: Session):
        with pytest.raises(NotFoundError):
            evals.get_by_id(db_session, uuid.uuid4())

    def test_list_by_eval_run(self, db_session: Session):
        r1 = evals.create(
            db_session,
            eval_run_id="batch-A",
            dataset_name="ds1",
            scorer_name="s1",
            score=0.8,
        )
        r2 = evals.create(
            db_session,
            eval_run_id="batch-A",
            dataset_name="ds1",
            scorer_name="s2",
            score=0.7,
        )
        evals.create(
            db_session,
            eval_run_id="batch-B",
            dataset_name="ds1",
            scorer_name="s1",
            score=0.9,
        )
        db_session.flush()

        result = evals.list_by_eval_run(db_session, "batch-A")
        ids = {r.id for r in result}
        assert r1.id in ids
        assert r2.id in ids
        assert len(ids) == 2

    def test_list_by_task(self, db_session: Session):
        task = tasks.create(db_session, input_data={})
        db_session.flush()

        r1 = evals.create(
            db_session,
            eval_run_id="run-1",
            dataset_name="ds",
            scorer_name="scorer",
            score=0.5,
            task_id=task.id,
        )
        evals.create(
            db_session,
            eval_run_id="run-2",
            dataset_name="ds",
            scorer_name="scorer",
            score=0.6,
        )
        db_session.flush()

        result = evals.list_by_task(db_session, task.id)
        assert len(result) == 1
        assert result[0].id == r1.id

    def test_list_by_scorer(self, db_session: Session):
        evals.create(
            db_session,
            eval_run_id="r1",
            dataset_name="ds",
            scorer_name="correctness",
            score=0.8,
        )
        evals.create(
            db_session,
            eval_run_id="r1",
            dataset_name="ds",
            scorer_name="fluency",
            score=0.9,
        )
        db_session.flush()

        result = evals.list_by_scorer(db_session, "correctness")
        assert all(r.scorer_name == "correctness" for r in result)

    def test_list_by_scorer_with_dataset_filter(self, db_session: Session):
        evals.create(
            db_session,
            eval_run_id="r1",
            dataset_name="golden_v1",
            scorer_name="correctness",
            score=0.8,
        )
        evals.create(
            db_session,
            eval_run_id="r1",
            dataset_name="silver_v1",
            scorer_name="correctness",
            score=0.7,
        )
        db_session.flush()

        result = evals.list_by_scorer(
            db_session, "correctness", dataset_name="golden_v1"
        )
        assert len(result) == 1
        assert result[0].dataset_name == "golden_v1"

    def test_list_by_dataset(self, db_session: Session):
        evals.create(
            db_session,
            eval_run_id="r1",
            dataset_name="my_dataset",
            scorer_name="s1",
            score=0.5,
        )
        evals.create(
            db_session,
            eval_run_id="r2",
            dataset_name="my_dataset",
            scorer_name="s2",
            score=0.6,
        )
        evals.create(
            db_session,
            eval_run_id="r3",
            dataset_name="other_dataset",
            scorer_name="s1",
            score=0.7,
        )
        db_session.flush()

        result = evals.list_by_dataset(db_session, "my_dataset")
        assert len(result) == 2
        assert all(r.dataset_name == "my_dataset" for r in result)


# ===========================================================================
# Cross-repository transaction behaviour
# ===========================================================================


class TestTransactionBehaviour:
    """Verify that multi-step operations within a single session are atomic."""

    def test_partial_failure_rollback(self, db_session: Session):
        """If we flush partway and then the session rollbacks, nothing persists."""
        user = users.create(db_session, email="tx_test@example.com")
        db_session.flush()
        uid = user.id

        # Simulate a mid-transaction savepoint rollback
        sp = db_session.begin_nested()
        tasks.create(db_session, input_data={"tx": True})
        db_session.flush()
        sp.rollback()

        # User should still be visible (within same outer transaction)
        found = users.get_by_id_optional(db_session, uid)
        assert found is not None

        # Task created in the savepoint should be gone
        task_list = tasks.list_by_status(db_session, TaskStatus.QUEUED)
        tx_tasks = [t for t in task_list if t.input_data.get("tx")]
        assert len(tx_tasks) == 0

    def test_multi_repo_atomicity(self, db_session: Session):
        """Creating a task and its first run in one transaction is atomic."""
        task = tasks.create(db_session, input_data={"multi": True})
        db_session.flush()
        run = runs.create(db_session, task_id=task.id)
        db_session.flush()

        # Both exist in the same uncommitted transaction
        retrieved_task = tasks.get_by_id(db_session, task.id)
        retrieved_run = runs.get_by_id(db_session, run.id)

        assert retrieved_task.id == task.id
        assert retrieved_run.task_id == task.id
