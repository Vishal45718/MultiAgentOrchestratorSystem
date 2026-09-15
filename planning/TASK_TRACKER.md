# Task Tracker

Statuses: `TODO / IN_PROGRESS / BLOCKED / DONE / NEEDS_REVIEW`

| ID | Task | Status | Dependencies | Acceptance Criteria |
|---|---|---|---|---|
| P1-T1 | Create repo tree with placeholders | DONE | — | Directory structure matches docs/ARCHITECTURE.md §11 |
| P1-T2 | pyproject.toml + lint/format config | DONE | P1-T1 | `pip install` and lint run cleanly |
| P1-T3 | docker-compose.yml (all services) | DONE | P1-T1 | `docker compose up` starts without error |
| P1-T4 | .env.example + config.py | DONE | P1-T1 | Config loads from env in a test |
| P1-T5 | Init planning/ files + AGENTS.md | DONE | — | All planning files present and non-empty |
| P2-T1 | SQLAlchemy models | DONE | P1-T3 | Models import without error |
| P2-T2 | Alembic init + first migration | DONE | P2-T1 | Migration applies to fresh DB |
| P2-T3 | Repository layer (CRUD) | TODO | P2-T2 | CRUD integration tests pass |
| P2-T4 | scripts/init_db.sh | TODO | P2-T2 | Script provisions DB from clean state |
| P3-T1 | Tool registry | TODO | P1-T2 | Register/list/validate covered by tests |
| P3-T2 | Tool JSON schemas | TODO | P3-T1 | Each tool has a valid schema file |
| P3-T3 | OpenAI function-calling adapter | TODO | P3-T1 | Adapter unit tests pass |
| P3-T4 | Anthropic tool-use adapter | TODO | P3-T1 | Adapter unit tests pass |
| P3-T5 | KB retrieval + mock tool | TODO | P3-T2 | Both tools callable via registry |
| P4-T1 | Graph state definition | TODO | P2-T1 | Typed state passes mypy/tests |
| P4-T2 | Router+Executor graph | TODO | P3-T5, P4-T1 | Synchronous run produces stored result |
| P4-T3 | Redis checkpointer | TODO | P4-T2 | Resume-after-crash test passes |
| P4-T4 | LLM client wrappers | TODO | — | Both providers callable behind one interface |
| P5-T1 | Chroma semantic store | TODO | P1-T3 | Embed/query round trip test passes |
| P5-T2 | Researcher agent | TODO | P5-T1, P3-T5 | Produces retrieval-grounded output in test |
| P5-T3 | Critic agent | TODO | P4-T2 | Correctly routes on synthetic low-confidence case |
| P5-T4 | Full multi-agent graph wiring | TODO | P5-T2, P5-T3 | Branch test covers finalize/retry/escalate |
| P6-T1 | Celery config (Redis broker) | TODO | P1-T3 | Worker starts and consumes a test task |
| P6-T2 | run_graph_task w/ retry policy | TODO | P6-T1, P5-T4 | Retry/backoff verified in test |
| P6-T3 | Circuit breaker → auto-escalate | TODO | P6-T2 | Forced failure triggers escalation |
| P6-T4 | Redis pub/sub status updates | TODO | P6-T2 | Status updates observable during run |
| P7-T1 | Escalation agent + hitl_requests repo | TODO | P2-T3, P5-T3 | Escalation persists a hitl_request row |
| P7-T2 | HITL endpoint stubs | TODO | P7-T1 | Endpoints return expected payloads (pre-wire) |
| P7-T3 | Resume-with-decision | TODO | P4-T3, P7-T1 | Full escalate→decide→resume test passes |
| P8-T1 | FastAPI app + deps | TODO | P1-T4 | App boots, `/health` returns 200 |
| P8-T2 | tasks routes | TODO | P6-T2 | Submit/status/list covered by API tests |
| P8-T3 | hitl routes | TODO | P7-T3 | HITL round trip via HTTP passes |
| P8-T4 | health routes | TODO | P8-T1 | Liveness/readiness pass in compose |
| P8-T5 | Pydantic schemas | TODO | P8-T1 | Requests/responses validated |
| P9-T1 | Streamlit submit page | TODO | P8-T2 | Manual test: task submitted successfully |
| P9-T2 | Streamlit status page | TODO | P8-T2 | Manual test: live status visible |
| P9-T3 | Streamlit HITL queue page | TODO | P8-T3 | Manual test: full HITL cycle from UI |
| P10-T1 | Structured logging | TODO | P8-T1 | Logs include task/correlation IDs |
| P10-T2 | OpenTelemetry tracing | TODO | P10-T1 | Spans present across API→Celery→graph→tools |
| P10-T3 | Metrics | TODO | P10-T1 | Latency/retry/escalation metrics exposed |
| P11-T1 | Eval dataset | TODO | P5-T4 | Dataset covers finalize/retry/escalate cases |
| P11-T2 | Scorers | TODO | P11-T1 | Scorer unit tests pass |
| P11-T3 | Eval runner + script | TODO | P11-T2 | Report generated and stored in Postgres |
| P12-T1 | API auth + rate limiting | TODO | P8-T1 | Unauthorized requests rejected in test |
| P12-T2 | Secrets/config review | TODO | P1-T4 | No secrets in repo; checklist signed off |
| P12-T3 | Hardened Dockerfile | TODO | P1-T3 | Non-root, healthchecks pass |
| P12-T4 | Load/soak test | TODO | P6-T2 | Target concurrency sustained, no unbounded queue growth |
| P12-T5 | Runbook | TODO | P10-T*, P7-T3 | Runbook reviewed and merged |
