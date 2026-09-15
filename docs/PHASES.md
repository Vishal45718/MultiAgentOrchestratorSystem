# Development Phases

Ordered by dependency. Each phase must reach its acceptance criteria before the next begins.

---

### Phase 1 — Foundations & Scaffolding
**Goal:** Runnable skeleton with tooling in place.
**Tasks:**
- P1-T1: Create repo tree (§ ARCHITECTURE.md) with empty `__init__.py`/placeholders.
- P1-T2: `pyproject.toml`, dependency pinning, linting/formatting config.
- P1-T3: `docker-compose.yml` (postgres, redis, chroma, api, worker, streamlit placeholders).
- P1-T4: `.env.example` + `src/config.py` (pydantic settings).
- P1-T5: Initialize `planning/*` files and `AGENTS.md`.
**Acceptance criteria:** `docker compose up` starts all containers without error; `pytest` runs (0 tests) cleanly.
**Tests:** smoke test asserting config loads from env.

---

### Phase 2 — Data Layer (PostgreSQL)
**Goal:** Durable schema for tasks, runs, messages, tool calls, HITL, audit log.
**Tasks:**
- P2-T1: SQLAlchemy models (`src/db/models.py`).
- P2-T2: Alembic setup + initial migration (`migrations/`).
- P2-T3: Repository layer (`src/db/repositories/`) with CRUD for tasks/runs/messages.
- P2-T4: `scripts/init_db.sh`.
**Acceptance criteria:** migration applies cleanly on fresh DB; repositories pass CRUD tests against a test DB.
**Tests:** integration tests using a disposable Postgres (testcontainers or docker-compose test profile).

---

### Phase 3 — Tool System
**Goal:** Model-agnostic tool registry with schema validation.
**Tasks:**
- P3-T1: `src/tools/registry.py` — register/list/validate tools.
- P3-T2: JSON schemas per tool (`src/tools/schemas/`).
- P3-T3: OpenAI function-calling adapter.
- P3-T4: Anthropic tool-use adapter.
- P3-T5: One real tool (`kb_retrieval_tool.py` stub) + one mock tool for tests.
**Acceptance criteria:** same tool schema produces valid call payloads for both providers.
**Tests:** unit tests per adapter; schema validation rejects malformed calls.

---

### Phase 4 — Single-Agent LangGraph Flow
**Goal:** Minimal graph (Router → Executor) with checkpointing.
**Tasks:**
- P4-T1: `src/graph/state.py` — typed graph state.
- P4-T2: `src/graph/build_graph.py` — Router + Executor nodes, conditional edges.
- P4-T3: Redis-backed checkpointer (`src/graph/checkpointer.py`).
- P4-T4: LLM client wrappers (`src/llm/openai_client.py`, `anthropic_client.py`, `router.py`).
**Acceptance criteria:** a task runs end-to-end synchronously and produces a stored result; interrupted run resumes from checkpoint.
**Tests:** unit test on state transitions; integration test on resume-after-crash.

---

### Phase 5 — Multi-Agent Graph & Semantic Memory
**Goal:** Add Researcher and Critic agents; wire ChromaDB RAG.
**Tasks:**
- P5-T1: `src/memory/semantic_store.py` — Chroma client, embed/query.
- P5-T2: `researcher_agent.py` using RAG + tool registry.
- P5-T3: `critic_agent.py` — confidence/risk scoring, routes to finalize/retry/escalate.
- P5-T4: Extend graph edges for the full Router→Researcher→Executor→Critic path.
**Acceptance criteria:** graph correctly branches to escalate on a synthetic low-confidence case.
**Tests:** unit tests per agent; graph-level test with mocked LLM responses for each branch.

---

### Phase 6 — Async Execution (Celery)
**Goal:** Move graph execution off the request path.
**Tasks:**
- P6-T1: `src/celery_app/celery_config.py` (Redis broker/backend).
- P6-T2: `src/celery_app/tasks.py` — `run_graph_task` with retry/backoff policy.
- P6-T3: Circuit breaker after N consecutive failures → auto-escalate.
- P6-T4: Status/pub-sub updates to Redis during execution.
**Acceptance criteria:** submitting a task returns immediately; worker completes it asynchronously; forced tool failure triggers retry then escalation.
**Tests:** integration test with Celery eager mode + failure injection.

---

### Phase 7 — Human-in-the-Loop
**Goal:** Full escalation and resume flow.
**Tasks:**
- P7-T1: `escalation_agent.py` + `hitl_requests` repository.
- P7-T2: FastAPI HITL endpoints (list pending, submit decision) — stub API, wired in Phase 8.
- P7-T3: Resume-from-checkpoint with injected human decision.
**Acceptance criteria:** a task escalated mid-run resumes correctly after a decision is recorded.
**Tests:** integration test simulating full escalate→decide→resume cycle.

---

### Phase 8 — FastAPI API Layer
**Goal:** External surface for the system.
**Tasks:**
- P8-T1: `src/api/main.py`, `deps.py`.
- P8-T2: `routes/tasks.py` — submit, get status, list.
- P8-T3: `routes/hitl.py` — pending queue, decision submission (connects Phase 7).
- P8-T4: `routes/health.py` — liveness/readiness.
- P8-T5: Pydantic request/response schemas.
**Acceptance criteria:** OpenAPI docs render; end-to-end task submission via HTTP works against dockerized stack.
**Tests:** API integration tests (httpx/TestClient) for each route, including HITL round trip.

---

### Phase 9 — Streamlit UI
**Goal:** Operator-facing UI for submission, monitoring, HITL review.
**Tasks:**
- P9-T1: `frontend/streamlit_app/pages/submit_task.py`.
- P9-T2: `pages/task_status.py` — polling/live status.
- P9-T3: `pages/hitl_queue.py` — review + decide.
**Acceptance criteria:** a human can submit a task, watch it run, and resolve an escalation entirely from the UI.
**Tests:** manual test checklist documented; smoke test that pages import/render without error.

---

### Phase 10 — Observability
**Goal:** Make the system debuggable and measurable.
**Tasks:**
- P10-T1: `src/observability/logging_config.py` — structured JSON logs, correlation/task IDs.
- P10-T2: `tracing.py` — OpenTelemetry spans across API → Celery → LangGraph → tools.
- P10-T3: `metrics.py` — task latency, retry counts, escalation rate, tool error rate.
**Acceptance criteria:** a single task's full lifecycle can be traced end-to-end by task ID across all logs.
**Tests:** test that logs contain required correlation fields; tracing spans present for a sample run.

---

### Phase 11 — Evaluation Harness
**Goal:** Quantify agent output quality over time.
**Tasks:**
- P11-T1: `src/evaluation/datasets/` — curated eval task set with expected outcomes.
- P11-T2: `scorers.py` — correctness, tool-call accuracy, escalation-appropriateness scorers.
- P11-T3: `eval_runner.py` + `scripts/run_eval.sh` — run eval set, output report, store results in Postgres.
**Acceptance criteria:** eval run produces a scored report; regressions are detectable by comparing runs.
**Tests:** unit tests for scorers; eval run completes on a small fixed dataset in CI.

---

### Phase 12 — Production Hardening
**Goal:** Ready for real deployment.
**Tasks:**
- P12-T1: API auth (API key or JWT) + rate limiting.
- P12-T2: Secrets management review, `.env.example` finalized, no secrets in repo.
- P12-T3: Dockerfile multi-stage build, non-root user, healthchecks in compose.
- P12-T4: Load/soak test of Celery + graph under concurrent tasks.
- P12-T5: Runbook: failure modes, escalation SLAs, rollback procedure (`docs/`).
**Acceptance criteria:** full stack passes load test at target concurrency without unbounded queue growth; security checklist signed off.
**Tests:** load test script + results recorded; security checklist test (no `.env` in image, no debug mode in prod config).
