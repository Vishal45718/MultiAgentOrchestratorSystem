# Decision Log

| ID | Date | Decision | Rationale | Alternatives Considered |
|---|---|---|---|---|
| D001 | init | LangGraph for orchestration | Explicit state graph, native checkpointing, fits multi-agent + HITL resume needs | Plain function-calling loop, CrewAI |
| D002 | init | PostgreSQL as sole system of record | Durable, relational, queryable audit trail; single source of truth | Store state only in Redis (rejected: not durable) |
| D003 | init | ChromaDB scoped to retrieval-only | Keeps vector store rebuildable and non-authoritative | Storing task state in Chroma metadata (rejected) |
| D004 | init | Redis limited to broker/cache/pub-sub | Avoid dual-source-of-truth risk with Postgres | Redis as primary state store (rejected) |
| D005 | init | Streamlit for MVP UI | Fast to build, sufficient for operator/HITL use case | Custom React frontend (deferred, not justified for MVP) |
| D006 | 2026-09-16 | SQLAlchemy 2.0 Declarative Models with Dialect-Agnostic Types | Use SQLAlchemy 2.0 `DeclarativeBase`, `Mapped[...]`, `Uuid` primary keys, `JSON().with_variant(JSONB, 'postgresql')`, and `native_enum=False`. Ensures type safety, full PostgreSQL optimization in production, and effortless in-memory SQLite unit testing without Docker requirements. | Integer auto-increment IDs, pure PostgreSQL-only types without dialect fallback, native Postgres enums. |

Add a new row for every non-trivial architectural choice or deviation from the
original plan. Never change architecture silently — log it here first.
